from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class CategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None

class CategoryResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    icon: Optional[str]
    color: Optional[str]

class DashboardViewCreate(BaseModel):
    name: str
    filters: Dict[str, Any]

class DashboardViewResponse(BaseModel):
    id: int
    name: str
    filters: Dict[str, Any]
    created_at: datetime
    updated_at: datetime