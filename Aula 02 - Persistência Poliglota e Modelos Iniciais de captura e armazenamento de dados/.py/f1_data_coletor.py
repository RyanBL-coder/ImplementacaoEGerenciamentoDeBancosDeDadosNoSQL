"""
f1_data_collector.py
--------------------
Coleta dados da API OpenF1 e armazena em MongoDB.

Endpoints:
    /sessions  -> collection sessions
    /drivers   -> collection drivers
    /laps      -> collection laps

Banco: openf1_data
Idempotência: update_one(..., upsert=True) usando chaves únicas.
"""

import os
import logging
import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from dotenv import load_dotenv

# ========================================================
# 1. Configuração de ambiente e logging
# ========================================================
load_dotenv()  # lê .env ANTES de qualquer os.getenv

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MONGO_DB_NAME = "openf1_data"
API_BASE_URL = "https://api.openf1.org/v1"

# Caso de demonstração (PDF): Corrida GP da Itália 2023 em Monza
SESSION_KEY = 9159
MEETING_KEY = 1219
YEAR = 2023

# ========================================================
# 2. Conexão com MongoDB (db global)
# ========================================================
db = None


def connect_mongodb() -> None:
    """Conecta ao MongoDB e popula a variável global `db`."""
    global db
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
        client.admin.command("ping")  # valida conexão
        db = client[MONGO_DB_NAME]
        logging.info("Conectado ao MongoDB (db=%s).", MONGO_DB_NAME)
    except PyMongoError as e:
        logging.exception("Falha ao conectar no MongoDB: %s", e)
        raise


# ========================================================
# 3. Busca de dados na API
# ========================================================
def fetch_data(endpoint: str, params: dict) -> list:
    """Faz GET na API OpenF1 e retorna a lista de resultados.

    Args:
        endpoint: ex. 'sessions', 'drivers', 'laps'
        params:   dict de query string
    Returns:
        list de dicionários (vazia em caso de erro).
    """
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        logging.info("%d registros obtidos de '%s'.", len(data), endpoint)
        return data
    except requests.RequestException as e:
        logging.exception("Falha ao buscar dados de '%s': %s", endpoint, e)
        return []


# ========================================================
# 4. Armazenamento no MongoDB (idempotente)
# ========================================================
def save_to_collection(data: list, collection_name: str, unique_keys: list) -> None:
    """Insere/atualiza registros usando upsert pelas chaves únicas.

    Usa a variável global `db`.

    Args:
        data:            lista de documentos
        collection_name: nome da collection destino
        unique_keys:     campos que formam a chave única
    """
    if db is None:
        logging.error("Conexão MongoDB não inicializada. Chame connect_mongodb() antes.")
        return

    if not data:
        logging.info("Nada para gravar em '%s'.", collection_name)
        return

    collection = db[collection_name]
    gravados = 0

    for record in data:
        query = {k: record.get(k) for k in unique_keys}
        if any(v is None for v in query.values()):
            logging.warning("Registro ignorado (chave única incompleta): %s", record)
            continue
        try:
            collection.update_one(query, {"$set": record}, upsert=True)
            gravados += 1
        except PyMongoError as e:
            logging.exception("Erro ao gravar em '%s': %s", collection_name, e)

    logging.info("%d/%d registros processados em '%s'.",
                 gravados, len(data), collection_name)


# ========================================================
# 5. Execução principal
# ========================================================
def main() -> None:
    connect_mongodb()

    # Passo 1: sessão específica
    sessions_data = fetch_data("sessions", {"session_key": SESSION_KEY})
    save_to_collection(sessions_data, "sessions", ["session_key"])

    # Passo 2: pilotos da sessão
    drivers_data = fetch_data("drivers", {"session_key": SESSION_KEY})
    save_to_collection(drivers_data, "drivers", ["session_key", "driver_number"])

    # Passo 3: voltas da sessão
    laps_data = fetch_data("laps", {"session_key": SESSION_KEY})
    save_to_collection(laps_data, "laps", ["session_key", "driver_number", "lap_number"])

    logging.info("Coleta finalizada com sucesso.")


if __name__ == "__main__":
    main()