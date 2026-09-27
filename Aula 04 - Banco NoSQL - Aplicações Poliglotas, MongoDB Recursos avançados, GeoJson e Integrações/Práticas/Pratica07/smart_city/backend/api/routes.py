from fastapi import APIRouter, HTTPException, Depends
from typing import List
from datetime import datetime
from bson import ObjectId
import json

from backend.db.mongodb import mongo_conn
from backend.db.sqlite import sqlite_conn
from backend.models.geo_models import SpatialDataCreate, SpatialDataResponse, GeospatialQuery
from backend.models.sql_models import CategoryCreate, CategoryResponse, DashboardViewCreate, DashboardViewResponse
from backend.db.sqlite import Category, DashboardView, AuditLog

router = APIRouter()

# ==================== MONGODB ROUTES ====================

@router.post("/spatial-data", response_model=SpatialDataResponse)
async def create_spatial_data(data: SpatialDataCreate):
    """Inserir novo dado geoespacial no MongoDB"""
    try:
        collection = mongo_conn.get_collection("spatial_data")
        
        document = {
            "name": data.name,
            "category": data.category,
            "geometry": data.geometry.dict(),
            "properties": data.properties,
            "timestamp": data.timestamp or datetime.utcnow(),
            "created_at": datetime.utcnow()
        }
        
        result = collection.insert_one(document)
        
        # Log de auditoria
        log_audit("CREATE_SPATIAL", {"id": str(result.inserted_id), "name": data.name})
        
        return {
            "id": str(result.inserted_id),
            "name": data.name,
            "category": data.category,
            "geometry": data.geometry.dict(),
            "properties": data.properties,
            "timestamp": data.timestamp
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spatial-data", response_model=List[SpatialDataResponse])
async def get_spatial_data(
    category: str = None,
    limit: int = 100
):
    """Consultar dados geoespaciais"""
    try:
        collection = mongo_conn.get_collection("spatial_data")
        query = {}
        
        if category:
            query["category"] = category
        
        results = collection.find(query).limit(limit)
        
        return [
            {
                "id": str(doc["_id"]),
                "name": doc["name"],
                "category": doc["category"],
                "geometry": doc["geometry"],
                "properties": doc.get("properties", {}),
                "timestamp": doc.get("timestamp")
            }
            for doc in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/spatial-data/query")
async def query_spatial_data(query: GeospatialQuery):
    """Executar queries geoespaciais complexas"""
    try:
        collection = mongo_conn.get_collection("spatial_data")
        mongo_query = {}
        
        # Filtro por categoria
        if query.category:
            mongo_query["category"] = query.category
        
        # Filtro por data
        if query.date_from or query.date_to:
            date_filter = {}
            if query.date_from:
                date_filter["$gte"] = query.date_from
            if query.date_to:
                date_filter["$lte"] = query.date_to
            mongo_query["timestamp"] = date_filter
        
        # Queries geoespaciais
        if query.query_type == "near" and query.coordinates:
            mongo_query["geometry"] = {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": query.coordinates
                    },
                    "$maxDistance": query.max_distance or 1000
                }
            }
        elif query.query_type == "within" and query.geometry:
            mongo_query["geometry"] = {
                "$geoWithin": {
                    "$geometry": query.geometry.dict()
                }
            }
        elif query.query_type == "intersects" and query.geometry:
            mongo_query["geometry"] = {
                "$geoIntersects": {
                    "$geometry": query.geometry.dict()
                }
            }
        
        results = collection.find(mongo_query)
        
        log_audit("QUERY_SPATIAL", {"type": query.query_type, "count": len(list(results.clone()))})
        
        return [
            {
                "id": str(doc["_id"]),
                "name": doc["name"],
                "category": doc["category"],
                "geometry": doc["geometry"],
                "properties": doc.get("properties", {})
            }
            for doc in results
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/analytics/aggregated")
async def get_aggregated_analytics():
    """Retornar dados agregados para gráficos"""
    try:
        collection = mongo_conn.get_collection("spatial_data")
        
        # Contagem por categoria
        category_counts = collection.aggregate([
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ])
        
        # Distribuição temporal (por mês)
        temporal_data = collection.aggregate([
            {"$group": {
                "_id": {
                    "year": {"$year": "$timestamp"},
                    "month": {"$month": "$timestamp"}
                },
                "count": {"$sum": 1}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ])
        
        return {
            "category_counts": list(category_counts),
            "temporal_data": list(temporal_data)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== SQLITE ROUTES ====================

@router.post("/categories", response_model=CategoryResponse)
async def create_category(category: CategoryCreate):
    """Criar nova categoria"""
    try:
        session = sqlite_conn.get_session()
        db_category = Category(
            name=category.name,
            description=category.description,
            icon=category.icon,
            color=category.color
        )
        session.add(db_category)
        session.commit()
        session.refresh(db_category)
        
        log_audit("CREATE_CATEGORY", {"name": category.name})
        
        return db_category
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories", response_model=List[CategoryResponse])
async def get_categories():
    """Listar todas as categorias"""
    try:
        session = sqlite_conn.get_session()
        categories = session.query(Category).all()
        return categories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/dashboard-views", response_model=DashboardViewResponse)
async def save_dashboard_view(view: DashboardViewCreate):
    """Salvar configuração de visualização do dashboard"""
    try:
        session = sqlite_conn.get_session()
        db_view = DashboardView(
            name=view.name,
            filters=view.filters
        )
        session.add(db_view)
        session.commit()
        session.refresh(db_view)
        
        log_audit("SAVE_VIEW", {"name": view.name})
        
        return db_view
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/dashboard-views", response_model=List[DashboardViewResponse])
async def get_dashboard_views():
    """Listar visualizações salvas"""
    try:
        session = sqlite_conn.get_session()
        views = session.query(DashboardView).order_by(DashboardView.created_at.desc()).all()
        return views
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/dashboard-views/{view_id}")
async def delete_dashboard_view(view_id: int):
    """Deletar visualização salva"""
    try:
        session = sqlite_conn.get_session()
        view = session.query(DashboardView).filter(DashboardView.id == view_id).first()
        if not view:
            raise HTTPException(status_code=404, detail="View não encontrada")
        
        session.delete(view)
        session.commit()
        
        log_audit("DELETE_VIEW", {"id": view_id})
        
        return {"message": "View deletada com sucesso"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==================== HELPER FUNCTIONS ====================

def log_audit(action: str, details: dict):
    """Registrar ação no log de auditoria"""
    try:
        session = sqlite_conn.get_session()
        log = AuditLog(action=action, details=details)
        session.add(log)
        session.commit()
    except Exception as e:
        print(f"Erro ao registrar log: {e}")