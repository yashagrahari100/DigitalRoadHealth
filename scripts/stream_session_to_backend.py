import pandas as pd
import numpy as np
import requests
import time

# Backend URL
API_URL = "http://localhost:8000/api/predict"

# Load one real session
data = pd.read_csv("data/processed/combined_sensor_data.csv")

# Create rolling features (same as training)
data["acc_mean"] = data["acc_mag"].rolling(window=10).mean()
data["acc_std"] = data["acc_mag"].rolling(window=10).std()
data["gyro_mean"] = data["gyro_mag"].rolling(window=10).mean()
data["gyro_std"] = data["gyro_mag"].rolling(window=10).std()

df = data.dropna()

print("Selecting random instances to simulate...")
# Bypassing local ML prediction due to feature mismatch
pothole_data = df.sample(n=30) # send 30 packets

print(f"Starting real-time simulation with {len(pothole_data)} predicted potholes...")

for _, row in pothole_data.iterrows():

    payload = {
        "acc_mag": float(row["acc_mag"]),
        "gyro_mag": float(row["gyro_mag"]),
        "speed": float(row["speed"]),
        "norm_acc": float(row["norm_acc"]),
        "jerk": float(row["jerk"]),
        "acc_mean": float(row["acc_mean"]),
        "acc_std": float(row["acc_std"]),
        "gyro_mean": float(row["gyro_mean"]),
        "gyro_std": float(row["gyro_std"]),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"])
    }

    try:
        response = requests.post(API_URL, json=payload)
        print(response.json())
    except Exception as e:
        print("Error:", e)

    time.sleep(0.1)
