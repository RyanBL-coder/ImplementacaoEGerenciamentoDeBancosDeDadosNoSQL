import os
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

# ========================================================
# 1. Carregando variáveis de ambiente
# ========================================================
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
API_BASE_URL = "https://api.openf1.org/v1"

# Parâmetros configuráveis
#SESSION_KEY = 9159   # Corrida GP Itália 2023 - Monza
#MEETING_KEY = 1219
#YEAR = 2023

SESSION_KEY = 9476   # Corrida GP Jeddah 2024 - Jeddah
MEETING_KEY = 1230
YEAR = 2024


# ========================================================
# 2. Função de conexão ao MongoDB
# ========================================================
def get_mongo_connection():
    """Conecta ao MongoDB e retorna o objeto do banco."""
    client = MongoClient(MONGO_URI)
    db = client["database_unipe_segunda-feira"]
    return db

# ========================================================
# 3. Função para buscar dados da API
# ========================================================
def fetch_data(endpoint: str, params: dict) -> list:
    """
    Busca dados da API OpenF1.

    Args:
        endpoint (str): Nome do endpoint, ex: 'sessions'
        params (dict): Parâmetros da query string
    Returns:
        list: Lista de registros retornados
    """
    url = f"{API_BASE_URL}/{endpoint}"
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f"[INFO] {len(data)} registros obtidos de '{endpoint}'.")
        return data
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao buscar dados de {endpoint}: {e}")
        return []

# ========================================================
# 4. Função para salvar dados no MongoDB (com prevenção de duplicatas)
# ========================================================
def save_to_collection(db, data: list, collection_name: str, unique_keys: list):
    """
    Salva ou atualiza dados no MongoDB, garantindo unicidade.

    Args:
        db: Objeto do banco de dados
        data (list): Lista de registros
        collection_name (str): Nome da collection
        unique_keys (list): Lista de campos que formam a chave única
    """
    collection = db[collection_name]

    for record in data:
        query = {key: record.get(key) for key in unique_keys}
        if None in query.values():
            print(f"[WARN] Registro ignorado por faltar chave única: {record}")
            continue
        collection.update_one(query, {"$set": record}, upsert=True)

    print(f"[INFO] {len(data)} registros processados na collection '{collection_name}'.")

# ========================================================
# 5. Fluxo Principal
# ========================================================
def main():
    db = get_mongo_connection()

    # ---- Passo 1: Coletar dados da sessão ----
    sessions_data = fetch_data("sessions", {"year": YEAR, "meeting_key": MEETING_KEY})
    save_to_collection(db, sessions_data, "sessions", ["session_key"])

    # ---- Passo 2: Coletar dados dos pilotos ----
    drivers_data = fetch_data("drivers", {"session_key": SESSION_KEY})
    save_to_collection(db, drivers_data, "drivers", ["session_key", "driver_number"])

    # ---- Passo 3: Coletar dados das voltas ----
    laps_data = fetch_data("laps", {"session_key": SESSION_KEY})
    save_to_collection(db, laps_data, "laps", ["session_key", "driver_number", "lap_number"])

    print("[SUCESSO] Coleta finalizada!")

# ========================================================
# 6. Execução direta do script
# ========================================================
if __name__ == "__main__":
    main()
