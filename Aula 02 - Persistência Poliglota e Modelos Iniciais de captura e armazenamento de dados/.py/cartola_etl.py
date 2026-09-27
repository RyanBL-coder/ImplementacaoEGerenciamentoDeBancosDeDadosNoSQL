
import os
import sys
import json
import time
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from pymongo import MongoClient, UpdateOne
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# ========================================================
# Configuração de logging
# ========================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
# Força timestamps em UTC no logger
logging.Formatter.converter = time.gmtime

# ========================================================
# Constantes e configuração
# ========================================================
API_BASE_URL = "https://api.cartola.globo.com"
MERCADO_ENDPOINT = f"{API_BASE_URL}/atletas/mercado"

load_dotenv()  # lê .env, se existir

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "database_cartola_fc")

# Coleções
COL_CLUBES = "clubes"
COL_ATLETAS = "atletas"
COL_MERCADO = "mercado"


# ========================================================
# Utilidades
# ========================================================
def iso_utc_now() -> str:
    """Retorna timestamp ISO-8601 em UTC."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


# ========================================================
# Módulo de Conexão
# ========================================================
def conectar_mongodb() -> MongoClient:
    """Estabelece conexão com o MongoDB e retorna o objeto de banco (db)."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        # Força uma chamada para validar a conexão
        client.admin.command("ping")
        db = client[MONGO_DB_NAME]
        logging.info("Conectado ao MongoDB com sucesso.")
        return db
    except Exception as e:
        logging.exception("Falha ao conectar no MongoDB: %s", e)
        raise


# ========================================================
# Módulo de Extração
# ========================================================
def buscar_dados_mercado(session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """Busca dados do endpoint de mercado no Cartola FC.

    Args:
        session: requests.Session opcional para reuso de conexão.

    Returns:
        dict com o JSON da resposta.
    """
    sess = session or requests.Session()
    headers = {
        "Accept": "application/json",
        "User-Agent": "cartola-etl/1.0 (+https://example.internal)",
    }

    # Retry simples com backoff exponencial
    max_tentativas = 3
    for tentativa in range(1, max_tentativas + 1):
        try:
            resp = sess.get(MERCADO_ENDPOINT, headers=headers, timeout=30)
            resp.raise_for_status()
            logging.info("Dados de mercado obtidos com sucesso (tentativa %d).", tentativa)
            return resp.json()
        except requests.RequestException as e:
            logging.warning("Erro na requisição (tentativa %d/%d): %s", tentativa, max_tentativas, e)
            if tentativa == max_tentativas:
                logging.exception("Falha ao buscar dados do mercado após %d tentativas.", max_tentativas)
                raise
            time.sleep(2 ** tentativa)  # backoff: 2, 4


# ========================================================
# Módulo de Transformação e Carga (ETL Core)
# ========================================================
def processar_e_gravar_dados(db, dados_mercado: Dict[str, Any]) -> None:
    """Processa o JSON de mercado e grava nas coleções do MongoDB.

    - clubes_rodada_atual: upsert por _id (id do clube).
    - atletas_rodada_atual: substitui documentos pela coleta atual (limpa e insere).
    - mercado_rodada_atual: mantém somente o status mais recente (limpa e insere).
    """
    timestamp = iso_utc_now()

    # --------- 1) Clubes ---------
    clubes_obj = dados_mercado.get("clubes", {})
    if isinstance(clubes_obj, dict):
        # Em geral, "clubes" vem como dict { "ID": {dados}, ... }
        ops: List[UpdateOne] = []
        for club_id_str, club_data in clubes_obj.items():
            try:
                club_id = int(club_id_str)
            except (TypeError, ValueError):
                # Às vezes já vem inteiro; tentar pegar do campo 'id'
                club_id = club_data.get("id")
                if club_id is None:
                    logging.warning("Clube com ID inválido será ignorado: %s", club_data)
                    continue

            doc = {
                "_id": club_id,
                "nome": club_data.get("nome"),
                "abreviacao": club_data.get("abreviacao"),
                "escudos": club_data.get("escudos"),
                "nome_fantasia": club_data.get("nome_fantasia"),
                "timestamp_coleta": timestamp,
            }
            ops.append(
                UpdateOne(
                    {"_id": doc["_id"]},
                    {"$set": doc},
                    upsert=True,
                )
            )

        if ops:
            try:
                result = db[COL_CLUBES].bulk_write(ops, ordered=False)
                upserts = (result.upserted_count or 0)
                modified = (result.modified_count or 0)
                logging.info("Clubes upsert: %d, modificados: %d.", upserts, modified)
            except PyMongoError as e:
                logging.exception("Erro ao gravar clubes: %s", e)
                raise
    else:
        logging.warning("Campo 'clubes' não está no formato esperado (dict).")


    # --------- 2) Atletas ---------
    atletas_list = dados_mercado.get("atletas", [])
    if not isinstance(atletas_list, list):
        logging.warning("Campo 'atletas' não é uma lista. Valor: %s", type(atletas_list))
        atletas_list = []

    for atleta in atletas_list:
        atleta["timestamp_coleta"] = timestamp

    try:
        # Mantém apenas a coleta atual
        delete_res = db[COL_ATLETAS].delete_many({})
        logging.info("Removidos %d documentos antigos de atletas.", delete_res.deleted_count)
        if atletas_list:
            db[COL_ATLETAS].insert_many(atletas_list, ordered=False)
            logging.info("Inseridos %d atletas.", len(atletas_list))
        else:
            logging.info("Nenhum atleta para inserir.")
    except PyMongoError as e:
        logging.exception("Erro ao gravar atletas: %s", e)
        raise


    # --------- 3) Status/Mercado ---------
    # Alguns campos úteis: rodada_atual, status_mercado, aviso, fechamento{...}
    mercado_doc = {
        "rodada_atual": dados_mercado.get("rodada_atual"),
        "status_mercado": dados_mercado.get("status_mercado"),
        "aviso": dados_mercado.get("aviso"),
        "fechamento": dados_mercado.get("fechamento"),
        "timestamp_coleta": timestamp,
    }

    try:
        db[COL_MERCADO].delete_many({})  # mantém apenas o status mais recente
        db[COL_MERCADO].insert_one(mercado_doc)
        logging.info("Status do mercado gravado com sucesso.")
    except PyMongoError as e:
        logging.exception("Erro ao gravar status do mercado: %s", e)
        raise

# ========================================================
# Orquestração
# ========================================================
def main() -> int:
    logging.info("Iniciando ETL Cartola FC...")
    try:
        db = conectar_mongodb()
        logging.info("Buscando dados na API do Cartola FC...")
        dados = buscar_dados_mercado()
        logging.info("Processando e gravando dados...")
        processar_e_gravar_dados(db, dados)
        logging.info("Finalizado com sucesso.")
        return 0
    except Exception as e:
        logging.error("Execução encerrada com erro: %s", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
