from sqlalchemy import create_engine, Column, Integer, String, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

Base = declarative_base()

class Category(Base):
    __tablename__ = 'categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    icon = Column(String(50))
    color = Column(String(20))

class DashboardView(Base):
    __tablename__ = 'dashboard_views'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    filters = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    action = Column(String(50), nullable=False)
    details = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow)

class SQLiteConnection:
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        
    def connect(self):
        try:
            db_path = os.getenv("SQLITE_DB_PATH", "smart_city.db")
            self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
            Base.metadata.create_all(self.engine)
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            print("✅ SQLite conectado com sucesso")
            return True
        except Exception as e:
            print(f"❌ Erro ao conectar no SQLite: {e}")
            return False
    
    def get_session(self):
        if self.SessionLocal is None:
            self.connect()
        return self.SessionLocal()

# Instância global
sqlite_conn = SQLiteConnection()