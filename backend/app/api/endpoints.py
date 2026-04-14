from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.pothole import SensorDataInput, PredictionResponse, PotholeResponse
from app.models.pothole import Pothole
from app.services.ml_service import ml_service
from typing import List

router = APIRouter()

@router.post("/predict", response_model=PredictionResponse)
def predict_pothole(sensor_data: SensorDataInput, db: Session = Depends(get_db)):
    try:
        # Convert Pydantic model to dict
        data_dict = sensor_data.dict()
        
        # Make prediction
        is_anomaly, anomaly_type, severity = ml_service.predict(data_dict)
        
        if is_anomaly:
            from datetime import datetime, timezone
            
            # Clustering logic
            RADIUS_DEG = 0.00015 # Approx 15 meters
            nearby_anomaly = db.query(Pothole).filter(
                Pothole.anomaly_type == anomaly_type,
                Pothole.latitude >= sensor_data.latitude - RADIUS_DEG,
                Pothole.latitude <= sensor_data.latitude + RADIUS_DEG,
                Pothole.longitude >= sensor_data.longitude - RADIUS_DEG,
                Pothole.longitude <= sensor_data.longitude + RADIUS_DEG
            ).first()

            if nearby_anomaly:
                nearby_anomaly.report_count += 1
                nearby_anomaly.last_reported = datetime.now(timezone.utc)
                db.commit()
                db.refresh(nearby_anomaly)
                db_pothole = nearby_anomaly
            else:
                # Store in database
                db_pothole = Pothole(
                    latitude=sensor_data.latitude,
                    longitude=sensor_data.longitude,
                    anomaly_type=anomaly_type,
                    severity=severity
                )
                db.add(db_pothole)
                db.commit()
                db.refresh(db_pothole)
            
            return PredictionResponse(
                is_anomaly=True,
                anomaly_type=anomaly_type,
                severity=severity,
                message=f"{anomaly_type.replace('_', ' ').title()} detected and stored."
            )
            
        return PredictionResponse(
            is_anomaly=False,
            message="No anomaly detected."
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/potholes", response_model=List[PotholeResponse])
def get_potholes(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    from datetime import datetime, timezone, timedelta
    twelve_hours_ago = datetime.now(timezone.utc) - timedelta(hours=12)
    
    # Verification & Decay filters
    potholes = db.query(Pothole).filter(
        Pothole.report_count >= 2,
        Pothole.last_reported >= twelve_hours_ago
    ).offset(skip).limit(limit).all()
    
    return potholes
