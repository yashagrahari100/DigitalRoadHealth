from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class SensorReading(BaseModel):
    timestamp: int
    accX: float
    accY: float
    accZ: float
    gyroX: float
    gyroY: float
    gyroZ: float

class SensorDataInput(BaseModel):
    speed: float
    latitude: float
    longitude: float
    readings: List[SensorReading]

class PredictionResponse(BaseModel):
    is_anomaly: bool
    anomaly_type: Optional[str] = None
    severity: Optional[str] = None
    message: str

class PotholeCreate(BaseModel):
    latitude: float
    longitude: float
    anomaly_type: str = "pothole"
    severity: str

class PotholeResponse(PotholeCreate):
    id: int
    timestamp: datetime
    report_count: int = 1

    class Config:
        from_attributes = True
