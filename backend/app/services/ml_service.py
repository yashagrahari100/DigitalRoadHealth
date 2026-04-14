import joblib
import pandas as pd
import numpy as np
from scipy import signal
from typing import Tuple, Optional, Dict, Any, List
import os

def apply_lowpass_filter(data: np.ndarray, cutoff_hz: float = 10.0, fs: float = 50.0) -> np.ndarray:
    if len(data) < 15:
        return data # Too short to filter effectively
    nyq = 0.5 * fs
    normal_cutoff = cutoff_hz / nyq
    b, a = signal.butter(4, normal_cutoff, btype='low', analog=False)
    try:
        y = signal.filtfilt(b, a, data)
        return y
    except ValueError:
        return data

def extract_features(readings: List[Dict[str, Any]]) -> Optional[pd.DataFrame]:
    if len(readings) < 10:
        return None
    
    # We estimate sampling frequency based on timestamp if needed, but typically assume ~50Hz
    # readings: timestamp, accX, accY, accZ, gyroX, gyroY, gyroZ
    
    acc_x = np.array([r['accX'] for r in readings])
    acc_y = np.array([r['accY'] for r in readings])
    acc_z = np.array([r['accZ'] for r in readings])
    
    gyro_x = np.array([r['gyroX'] for r in readings])
    gyro_y = np.array([r['gyroY'] for r in readings])
    gyro_z = np.array([r['gyroZ'] for r in readings])

    # Apply Butterworth low-pass filter to strip engine chatter
    acc_x = apply_lowpass_filter(acc_x)
    acc_y = apply_lowpass_filter(acc_y)
    acc_z = apply_lowpass_filter(acc_z)

    # Dynamic projection of gravity: simply remove the mean over this short window
    acc_x = acc_x - np.mean(acc_x)
    acc_y = acc_y - np.mean(acc_y)
    acc_z = acc_z - np.mean(acc_z)

    # Calculate 3D magnitudes
    acc_mag = np.sqrt(acc_x**2 + acc_y**2 + acc_z**2)
    gyro_mag = np.sqrt(gyro_x**2 + gyro_y**2 + gyro_z**2)

    # Compute features required by RF model
    features = {
        'acc_mean': float(np.mean(acc_mag)),
        'acc_max': float(np.max(acc_mag)),
        'acc_min': float(np.min(acc_mag)),
        'acc_std': float(np.std(acc_mag)),
        'acc_jerk': float(np.max(acc_mag) - np.min(acc_mag)),
        'gyr_mean': float(np.mean(gyro_mag)),
        'gyr_max': float(np.max(gyro_mag)),
        'gyr_min': float(np.min(gyro_mag)),
        'gyr_std': float(np.std(gyro_mag)),
        'gyr_jerk': float(np.max(gyro_mag) - np.min(gyro_mag))
    }

    return pd.DataFrame([features])

def calculate_severity_rf(acc_jerk: float) -> str:
    if acc_jerk > 40:
        return "High"
    elif acc_jerk > 20:
        return "Medium"
    else:
        return "Low"

class MLService:
    def __init__(self):
        self.model = None
        self._load_model()
    
    def _load_model(self):
        model_path = os.path.join(os.path.dirname(__file__), "../models/random_forest_model.pkl")
        try:
            with open(model_path, "rb") as f:
                self.model = joblib.load(f)
            print(f"Model loaded successfully from {model_path}")
        except Exception as e:
            print(f"Error loading model from {model_path}: {e}")

    def predict(self, sensor_data: dict) -> Tuple[bool, Optional[str], Optional[str]]:
        speed = sensor_data.get('speed', 0.0)
        
        # 1. Speed Thresholding to avoid false positives in parking/traffic
        if speed < 2.0:
            return False, None, None

        readings = sensor_data.get('readings', [])
        if not readings:
            return False, None, None

        # 2. Extract features (with Low-pass filtering and Gravity subtraction)
        features_df = extract_features(readings)
        if features_df is None:
            return False, None, None

        # 3. Model Inference
        if self.model is not None:
            try:
                # Ensure correct feature order
                feature_order = ['acc_mean', 'acc_max', 'acc_min', 'acc_std', 'acc_jerk', 'gyr_mean', 'gyr_max', 'gyr_min', 'gyr_std', 'gyr_jerk']
                X = features_df[feature_order]
                
                prediction = self.model.predict(X)[0]
                probabilities = self.model.predict_proba(X)[0]
                confidence = max(probabilities)

                if prediction == "normal_road":
                    return False, None, None

                # 4. Severity computation based on jerk
                acc_jerk = float(features_df['acc_jerk'].iloc[0])
                severity = calculate_severity_rf(acc_jerk)

                # Optional hooked for pseudo-labeling Phase 2
                if confidence > 0.85:
                    print(f"High-confidence {prediction} detected (proba: {confidence:.2f})")
                
                return True, str(prediction), severity

            except Exception as e:
                print(f"Error during ML inference: {e}")
        
        return False, None, None

ml_service = MLService()
