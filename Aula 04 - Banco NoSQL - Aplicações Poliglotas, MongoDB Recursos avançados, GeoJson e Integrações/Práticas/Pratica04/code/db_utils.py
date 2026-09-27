# db_utils.py (híbrido: MongoDB real + mock fallback)
import os
import random
import requests
import pandas as pd
from datetime import datetime
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

OPENF1_API_URL = os.getenv("OPENF1_API_URL", "https://api.openf1.org/v1")

# ==========================================================
# --- Conexão ao MongoDB ---
# ==========================================================
def get_mongo_db():
    mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("MONGO_DB", "openf1_data")

    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2000)
        client.admin.command("ping")
        return client[db_name]
    except ConnectionFailure:
        print("⚠️ Não foi possível conectar ao MongoDB. Operando com API OpenF1 / Fallback Direct.")
        return None

# ==========================================================
# --- Helper de Requisição HTTP OpenF1 API ---
# ==========================================================
def _fetch_from_openf1(endpoint, params=None):
    try:
        url = f"{OPENF1_API_URL}/{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"⚠️ Erro ao consultar API OpenF1 ({endpoint}): {e}")
        return None

# ==========================================================
# --- Funções Híbridas (MongoDB -> OpenF1 API -> Mock) ---
# ==========================================================
def get_race_sessions(db, year):
    # 1. Tenta via MongoDB
    if db is not None:
        sessions = list(db.sessions.find({"year": int(year)}, {"_id": 0}))
        if sessions:
            return sessions

    # 2. Tenta via API OpenF1
    api_data = _fetch_from_openf1("sessions", {"year": year, "session_name": "Race"})
    if api_data:
        # Formata os dados para o padrão interno
        sessions = []
        for s in api_data:
            session_obj = {
                "session_key": str(s.get("session_key")),
                "race_name": s.get("meeting_name") or f"GP {s.get('country_name')}",
                "session_name": s.get("session_name"),
                "year": s.get("year"),
                "country_name": s.get("country_name"),
                "circuit_short_name": s.get("circuit_short_name"),
                "date_start": s.get("date_start")
            }
            sessions.append(session_obj)

        # Salva no cache do MongoDB se disponível
        if db is not None and sessions:
            try:
                db.sessions.insert_many(sessions, ordered=False)
            except Exception:
                pass

        return sessions

    # 3. Fallback para Mock
    return _mock_get_race_sessions(year)


def get_session_details(db, session_key):
    if db is not None:
        session = db.sessions.find_one({"session_key": str(session_key)}, {"_id": 0})
        if session:
            return session

    # Busca na API se não achou localmente
    api_data = _fetch_from_openf1("sessions", {"session_key": session_key})
    if api_data and len(api_data) > 0:
        s = api_data[0]
        return {
            "session_key": str(s.get("session_key")),
            "year": s.get("year"),
            "country_name": s.get("country_name"),
            "circuit_short_name": s.get("circuit_short_name"),
            "date_start": s.get("date_start"),
        }

    return _mock_get_session_details(str(session_key))


def get_drivers_from_session(db, session_key):
    if db is not None:
        drivers = list(db.drivers.find({"session_key": str(session_key)}, {"_id": 0}))
        if drivers:
            return drivers

    # Busca na API OpenF1
    api_data = _fetch_from_openf1("drivers", {"session_key": session_key})
    if api_data:
        drivers = []
        for d in api_data:
            drivers.append({
                "session_key": str(session_key),
                "driver_number": d.get("driver_number"),
                "full_name": d.get("full_name") or d.get("broadcast_name"),
                "team_name": d.get("team_name", "N/A"),
                "name_acronym": d.get("name_acronym")
            })

        if db is not None and drivers:
            try:
                db.drivers.insert_many(drivers, ordered=False)
            except Exception:
                pass

        return drivers

    return _mock_get_drivers_from_session(str(session_key))


def get_laps_for_drivers(db, session_key, driver_numbers):
    if db is not None:
        laps = list(
            db.laps.find(
                {"session_key": str(session_key), "driver_number": {"$in": driver_numbers}},
                {"_id": 0}
            )
        )
        if laps:
            return pd.DataFrame(laps)

    # Busca dados por piloto na API OpenF1
    all_laps = []
    for driver_num in driver_numbers:
        api_data = _fetch_from_openf1("laps", {"session_key": session_key, "driver_number": driver_num})
        if api_data:
            for l in api_data:
                # O OpenF1 fornece 'lap_duration' em segundos
                all_laps.append({
                    "session_key": str(session_key),
                    "driver_number": l.get("driver_number"),
                    "lap_number": l.get("lap_number"),
                    "lap_duration": l.get("lap_duration")
                })

    if all_laps:
        if db is not None:
            try:
                db.laps.insert_many(all_laps, ordered=False)
            except Exception:
                pass
        return pd.DataFrame(all_laps)

    return _mock_get_laps_for_drivers(str(session_key), driver_numbers)


# ==========================================================
# --- MOCKS (fallback final) ---
# ==========================================================
def _mock_get_race_sessions(year):
    return [
        {"session_key": f"{year}_AUS_GP", "race_name": "GP da Austrália", "session_name": "Corrida"},
        {"session_key": f"{year}_BRA_GP", "race_name": "GP do Brasil", "session_name": "Corrida"},
        {"session_key": f"{year}_MON_GP", "race_name": "GP de Mônaco", "session_name": "Corrida"},
    ]


def _mock_get_session_details(session_key):
    return {
        "year": session_key.split("_")[0] if "_" in str(session_key) else "2024",
        "country_name": "Brasil" if "BRA" in str(session_key) else "Austrália",
        "circuit_short_name": "Interlagos" if "BRA" in str(session_key) else "Albert Park",
        "date_start": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
    }


def _mock_get_drivers_from_session(session_key):
    return [
        {"driver_number": 1, "full_name": "Max Verstappen", "team_name": "Red Bull Racing"},
        {"driver_number": 16, "full_name": "Charles Leclerc", "team_name": "Ferrari"},
        {"driver_number": 44, "full_name": "Lewis Hamilton", "team_name": "Mercedes"},
        {"driver_number": 63, "full_name": "George Russell", "team_name": "Mercedes"},
    ]


def _mock_get_laps_for_drivers(session_key, driver_numbers):
    laps_data = []
    for driver in driver_numbers:
        base_time = random.uniform(85, 95)
        for lap in range(1, 31):
            laps_data.append({
                "driver_number": driver,
                "lap_number": lap,
                "lap_duration": base_time + random.uniform(-2, 2)
            })
    return pd.DataFrame(laps_data)