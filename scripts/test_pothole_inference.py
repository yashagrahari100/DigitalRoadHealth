import requests
import time
import random
import sys

# Generate mock data
readings = []
timestamp_now = int(time.time() * 1000)
for i in range(100):
    val = random.uniform(1.0, 10.0)
    # Simulate a bump halfway
    if 40 <= i <= 60:
        val += 20.0
    readings.append({
        "timestamp": timestamp_now + (i * 20),
        "accX": val, "accY": 9.8, "accZ": val,
        "gyroX": 0.1, "gyroY": 0.1, "gyroZ": 0.1
    })

payload = {
    "speed": 5.0, # Will not trigger speed threshold constraint
    "latitude": 19.01,
    "longitude": 73.01,
    "readings": readings
}

print("Testing Model Inference with raw batches & filters...")
from app.services.ml_service import ml_service

# To test without starting API server, we just call ML service natively
# But ml_service might error out if it relies on pydantic objects in endpoint vs dict in test
res = ml_service.predict(payload)
print(f"Prediction Result: {res}")

if len(sys.argv) > 1 and sys.argv[1] == "api":
    import requests
    response = requests.post("http://localhost:8000/api/predict", json=payload)
    print("API Response:", response.text)
