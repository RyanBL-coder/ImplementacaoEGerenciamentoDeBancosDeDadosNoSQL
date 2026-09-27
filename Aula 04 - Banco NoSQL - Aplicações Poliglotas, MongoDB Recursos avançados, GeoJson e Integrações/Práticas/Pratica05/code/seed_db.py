import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# Carrega as variáveis de ambiente do .env
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "openf1_data")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "sqlite:///analysis_reports.db")

# ==========================================
# 1. SETUP DE MODELO DO SQLITE (SQLAlchemy)
# ==========================================
Base = declarative_base()

class RaceAnalysis(Base):
    __tablename__ = "race_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_name = Column(String(255), nullable=False)
    driver_name = Column(String(255), nullable=False)
    fastest_lap = Column(Float, nullable=True)
    average_lap_time = Column(Float, nullable=True)
    total_laps = Column(Integer, nullable=False)
    consistency_std_dev = Column(Float, nullable=True)
    analysis_timestamp = Column(DateTime, default=datetime.utcnow)

# ==========================================
# 2. POPULAR MONGODB (Dados Brutos/Semiestruturados)
# ==========================================
def seed_mongodb():
    print("⏳ Conectando ao MongoDB...")
    client = MongoClient(MONGODB_URI)
    db = client[MONGODB_DB_NAME]

    # Limpa coleções existentes antes de popular
    db["sessions"].drop()
    db["laps"].drop()

    sessions_data = [
        {
            "session_key": 9158,
            "year": 2023,
            "session_name": "Race",
            "location": "Monza",
            "country_name": "Italy",
            "circuit_short_name": "Monza",
            "date_start": "2023-09-03T13:00:00"
        },
        {
            "session_key": 9159,
            "year": 2023,
            "session_name": "Race",
            "location": "Interlagos",
            "country_name": "Brazil",
            "circuit_short_name": "São Paulo",
            "date_start": "2023-11-05T17:00:00"
        },
        {
            "session_key": 9160,
            "year": 2024,
            "session_name": "Race",
            "location": "Silverstone",
            "country_name": "Great Britain",
            "circuit_short_name": "Silverstone",
            "date_start": "2024-07-07T14:00:00"
        }
    ]

    # Inserção das Sessões
    db["sessions"].insert_many(sessions_data)
    print(f"✅ MongoDB: {len(sessions_data)} sessões inseridas na coleção 'sessions'.")

    # Mapeamento de pilotos fictícios
    drivers = [
        {"number": 16, "name": "Charles Leclerc"},
        {"number": 55, "name": "Carlos Sainz Jr."},
        {"number": 1, "name": "Max Verstappen"},
        {"number": 44, "name": "Lewis Hamilton"}
    ]

    laps_data = []

    # Gerador de voltas de corrida com tempos realistas
    for session in sessions_data:
        s_key = session["session_key"]
        total_laps_count = 25  # Simulação de 25 voltas por sessão

        for driver in drivers:
            base_time = random.uniform(80.0, 85.0)  # Tempo base de volta em segundos

            for lap_num in range(1, total_laps_count + 1):
                is_pit_out = (lap_num == 12)  # Simula volta de Pit Stop na volta 12
                
                if is_pit_out:
                    duration = base_time + random.uniform(20.0, 25.0)  # Adiciona tempo do pit stop
                else:
                    duration = base_time + random.uniform(-0.8, 1.2)  # Variação normal de desgaste

                lap_record = {
                    "session_key": s_key,
                    "driver_number": driver["number"],
                    "driver_name": driver["name"],
                    "lap_number": lap_num,
                    "lap_duration": round(duration, 3),
                    "is_pit_out_lap": is_pit_out,
                    "sector_1": round(duration * 0.3, 3),
                    "sector_2": round(duration * 0.4, 3),
                    "sector_3": round(duration * 0.3, 3)
                }
                laps_data.append(lap_record)

    # Inserção das Voltas
    db["laps"].insert_many(laps_data)
    print(f"✅ MongoDB: {len(laps_data)} registros de voltas inseridos na coleção 'laps'.")


# ==========================================
# 3. POPULAR SQLITE (Histórico de Resumos)
# ==========================================
def seed_sqlite():
    print("\n⏳ Conectando ao SQLite...")
    engine = create_engine(SQLITE_DB_PATH, echo=False)
    
    # Recria a tabela
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    db_session = SessionLocal()

    # Histórico pré-existente de relatórios de análises salvas
    dummy_reports = [
        RaceAnalysis(
            session_name="Monza - Race (Italy)",
            driver_name="16",
            fastest_lap=80.124,
            average_lap_time=81.450,
            total_laps=25,
            consistency_std_dev=0.612,
            analysis_timestamp=datetime.now() - timedelta(days=2)
        ),
        RaceAnalysis(
            session_name="Monza - Race (Italy)",
            driver_name="55",
            fastest_lap=80.350,
            average_lap_time=81.720,
            total_laps=25,
            consistency_std_dev=0.745,
            analysis_timestamp=datetime.now() - timedelta(days=2)
        ),
        RaceAnalysis(
            session_name="Interlagos - Race (Brazil)",
            driver_name="1",
            fastest_lap=71.890,
            average_lap_time=72.910,
            total_laps=25,
            consistency_std_dev=0.320,
            analysis_timestamp=datetime.now() - timedelta(hours=5)
        )
    ]

    try:
        db_session.add_all(dummy_reports)
        db_session.commit()
        print(f"✅ SQLite: {len(dummy_reports)} relatórios históricos inseridos no banco 'analysis_reports.db'.")
    except Exception as e:
        db_session.rollback()
        print(f"❌ Erro ao popular o SQLite: {e}")
    finally:
        db_session.close()


if __name__ == "__main__":
    print("🏁 Iniciando o povoamento dos bancos de dados (Persistência Poliglota)...")
    seed_mongodb()
    seed_sqlite()
    print("\n🚀 Todos os dados fictícios foram gerados com sucesso!")