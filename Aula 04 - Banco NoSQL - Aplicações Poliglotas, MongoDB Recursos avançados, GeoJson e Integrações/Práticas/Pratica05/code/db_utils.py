import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from pymongo import MongoClient
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, inspect
from sqlalchemy.orm import declarative_base, sessionmaker

# Carrega as variáveis de ambiente
load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "openf1_data")
SQLITE_DB_PATH = os.getenv("SQLITE_DB_PATH", "sqlite:///analysis_reports.db")

# ==========================================
# CONFIGURAÇÕES E CONEXÕES MONGODB
# ==========================================

def get_mongo_client():
    """Retorna a instância do cliente MongoDB."""
    return MongoClient(MONGODB_URI)

def get_mongo_db():
    """Retorna o banco de dados MongoDB."""
    client = get_mongo_client()
    return client[MONGODB_DB_NAME]

def fetch_years():
    """Busca os anos disponíveis na coleção de sessões do MongoDB."""
    db = get_mongo_db()
    sessions_col = db["sessions"]
    years = sessions_col.distinct("year")
    return sorted(years, reverse=True)

def fetch_sessions_by_year(year: int):
    """Retorna a lista de sessões disponíveis para um determinado ano."""
    db = get_mongo_db()
    sessions_col = db["sessions"]
    cursor = sessions_col.find({"year": year}, {"_id": 0, "session_key": 1, "location": 1, "country_name": 1, "session_name": 1, "circuit_short_name": 1})
    return list(cursor)

def fetch_laps_data(session_key: int):
    """Busca todas as voltas registradas para uma determinada sessão."""
    db = get_mongo_db()
    laps_col = db["laps"]
    cursor = laps_col.find({"session_key": session_key}, {"_id": 0})
    df = pd.DataFrame(list(cursor))
    return df

# ==========================================
# CONFIGURAÇÕES E OPERAÇÕES SQLITE (SQLAlchemy)
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

engine = create_engine(SQLITE_DB_PATH, echo=False)
SessionLocal = sessionmaker(bind=engine)

def init_sqlite_db():
    """Cria as tabelas no SQLite se não existirem."""
    Base.metadata.create_all(engine)

def save_analysis_reports(reports_data: list[dict]):
    """Salva uma lista de dicionários contendo os resumos agregados no SQLite."""
    init_sqlite_db()
    db_session = SessionLocal()
    try:
        for item in reports_data:
            record = RaceAnalysis(
                session_name=item["session_name"],
                driver_name=str(item["driver_name"]),
                fastest_lap=float(item["fastest_lap"]) if pd.notnull(item["fastest_lap"]) else None,
                average_lap_time=float(item["average_lap_time"]) if pd.notnull(item["average_lap_time"]) else None,
                total_laps=int(item["total_laps"]),
                consistency_std_dev=float(item["consistency_std_dev"]) if pd.notnull(item["consistency_std_dev"]) else None,
                analysis_timestamp=datetime.now()
            )
            db_session.add(record)
        db_session.commit()
    except Exception as e:
        db_session.rollback()
        raise e
    finally:
        db_session.close()

def fetch_analysis_history():
    """Lê todos os relatórios armazenados no SQLite."""
    init_sqlite_db()
    db_session = SessionLocal()
    try:
        query = db_session.query(RaceAnalysis).order_by(RaceAnalysis.analysis_timestamp.desc())
        df = pd.read_sql(query.statement, db_session.bind)
        return df
    finally:
        db_session.close()