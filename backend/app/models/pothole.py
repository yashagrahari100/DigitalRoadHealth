from sqlalchemy import Boolean, Column, Float, Integer, String, DateTime
from datetime import datetime, timezone
from app.core.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class Pothole(Base):
    __tablename__ = "potholes"

    id = Column(Integer, primary_key=True, index=True)
    latitude = Column(Float, index=True)
    longitude = Column(Float, index=True)
    anomaly_type = Column(String, default="pothole") # E.g., "pothole" or "speed_breaker"
    severity = Column(String) # E.g., Low, Medium, High
    timestamp = Column(DateTime, default=utc_now)
    
    # Clustering Columns
    report_count = Column(Integer, default=1)
    first_reported = Column(DateTime, default=utc_now)
    last_reported = Column(DateTime, default=utc_now)
