import pandas as pd
import numpy as np
import joblib
import matplotlib.pyplot as plt

# =========================
# CONFIG
# =========================

DATA_PATH = "../data/processed/combined_sensor_data.csv"
MODEL_PATH = "../model/pothole_model.pkl"

# =========================
# LOAD DATA
# =========================

print("Loading data and model...")

data = pd.read_csv(DATA_PATH)
model = joblib.load(MODEL_PATH)

print(f"Total rows: {len(data)}")

# =========================
# CREATE FEATURES (same as training)
# =========================

data["acc_mean"] = data["acc_mag"].rolling(window=10).mean()
data["acc_std"] = data["acc_mag"].rolling(window=10).std()
data["gyro_mean"] = data["gyro_mag"].rolling(window=10).mean()
data["gyro_std"] = data["gyro_mag"].rolling(window=10).std()

# Convert speed to km/h
data["speed_kmh"] = data["speed"] * 3.6

# Remove NaN rows
data = data.dropna()

# =========================
# FEATURE LIST
# =========================

features = [
    "acc_mag",
    "gyro_mag",
    "speed",
    "norm_acc",
    "jerk",
    "acc_mean",
    "acc_std",
    "gyro_mean",
    "gyro_std"
]

X = data[features]

# =========================
# PREDICT
# =========================

print("Predicting potholes...")

data["prediction"] = model.predict(X)

print("\nPrediction Summary:")
print(data["prediction"].value_counts())

# =========================
# SHOW POTHOLE DATA WITH SPEED
# =========================

potholes = data[data["prediction"] == 1]

print("\nSample pothole detections with speed:")

print(
    potholes[
        ["time", "acc_mag", "gyro_mag", "speed", "speed_kmh"]
    ].head(10)
)

# =========================
# VISUALIZATION
# =========================

plt.figure(figsize=(16,10))

# Acceleration plot
plt.subplot(2,1,1)

plt.plot(data.index, data["acc_mag"], label="Acceleration Magnitude")

plt.scatter(
    potholes.index,
    potholes["acc_mag"],
    color="red",
    label="Detected potholes"
)

plt.title("Acceleration and Pothole Detection")
plt.xlabel("Time Index")
plt.ylabel("Acceleration Magnitude")
plt.legend()

# Speed plot
plt.subplot(2,1,2)

plt.plot(data.index, data["speed_kmh"], color="green", label="Speed (km/h)")

plt.scatter(
    potholes.index,
    potholes["speed_kmh"],
    color="red",
    label="Pothole speed"
)

plt.title("Vehicle Speed During Detection")
plt.xlabel("Time Index")
plt.ylabel("Speed (km/h)")
plt.legend()

plt.tight_layout()
plt.show()

print("\nVisualization complete.")
