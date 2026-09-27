from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class GeometryType(str, Enum):
    POINT = "Point"
    LINESTRING = "LineString"
    POLYGON = "Polygon"
    MULTIPOINT = "MultiPoint"
    MULTILINESTRING = "MultiLineString"
    MULTIPOLYGON = "MultiPolygon"

class Geometry(BaseModel):
    type: GeometryType
    coordinates: List[Any]

class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: Geometry
    properties: Dict[str, Any]

class SpatialDataCreate(BaseModel):
    name: str
    category: str
    geometry: Geometry
    properties: Dict[str, Any] = Field(default_factory=dict)
    timestamp: Optional[datetime] = None

class SpatialDataResponse(BaseModel):
    id: str
    name: str
    category: str
    geometry: Geometry
    properties: Dict[str, Any]
    timestamp: Optional[datetime]

class GeospatialQuery(BaseModel):
    query_type: str  # near, within, intersects
    geometry: Optional[Geometry] = None
    coordinates: Optional[List[float]] = None
    max_distance: Optional[float] = None
    category: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None