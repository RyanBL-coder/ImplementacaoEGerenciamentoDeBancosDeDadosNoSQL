from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from backend.db.mongodb import mongo_conn
from backend.db.sqlite import sqlite_conn
from backend.api.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Iniciando aplicação...")
    mongo_conn.connect()
    mongo_conn.create_geospatial_index("spatial_data")
    sqlite_conn.connect()
    yield
    # Shutdown
    print("🛑 Encerrando aplicação...")
    mongo_conn.close()

app = FastAPI(
    title="Smart City Dashboard API",
    description="API para dashboard geoespacial de cidade inteligente",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {
        "message": "Smart City Dashboard API",
        "docs": "/docs",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)