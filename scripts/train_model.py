import pandas as pd
import numpy as np
import joblib
import os

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix

# =========================
# CONFIGURATION
# =========================

DATA_PATH = "../data/processed/combined_sensor_data.csv"
MODEL_PATH = "../model/pothole_model.pkl"

os.makedirs("../model/", exist_ok=True)

# =========================
# LOAD DATA
# =========================

print("Loading dataset...")
data = pd.read_csv(DATA_PATH)
print(f"Total rows loaded: {len(data)}")

# =========================
# BASIC FEATURE CHECK
# =========================

required_columns = ["acc_mag", "gyro_mag", "speed", "jerk", "time"]

for col in required_columns:
    if col not in data.columns:
        raise Exception(f"Missing required column: {col}")

# =========================
# ESTIMATE SAMPLING RATE
# =========================

time_diff = data["time"].diff().median()  # nanoseconds
sampling_rate = 1e9 / time_diff if time_diff > 0 else 50

print(f"Estimated sampling rate: {sampling_rate:.2f} Hz")

# =========================
# DETECT SPIKE FRAMES
# =========================

SPIKE_THRESHOLD = 18

data["is_spike"] = data["acc_mag"] > SPIKE_THRESHOLD

# Group consecutive spike frames
data["spike_group"] = (
    data["is_spike"] != data["is_spike"].shift()
).cumsum()

# =========================
# BUILD EVENT-LEVEL DATASET
# =========================

print("Building event-level dataset...")

event_rows = []

for group_id, group in data.groupby("spike_group"):

    # Skip non-spike groups
    if not group["is_spike"].iloc[0]:
        continue

    duration = len(group) / sampling_rate
    max_acc = group["acc_mag"].max()
    mean_acc = group["acc_mag"].mean()
    max_gyro = group["gyro_mag"].max()
    mean_speed = group["speed"].mean()
    max_jerk = group["jerk"].abs().max()

    event_rows.append([
        max_acc,
        mean_acc,
        max_gyro,
        mean_speed,
        duration,
        max_jerk
    ])

event_df = pd.DataFrame(event_rows, columns=[
    "max_acc",
    "mean_acc",
    "max_gyro",
    "mean_speed",
    "duration",
    "max_jerk"
])

print(f"Total spike events detected: {len(event_df)}")

# =========================
# LABEL EVENTS (Initial Rule)
# =========================

print("Creating event labels...")

def event_label(row):

    if row["mean_speed"] * 3.6 < 3:
        return 0

    if row["duration"] < 0.08 and row["max_acc"] > 25:
        return 1

    return 0

event_df["label"] = event_df.apply(event_label, axis=1)

print(event_df.describe())
print(event_df[event_df["label"] == 1][["duration","max_acc"]].describe())
print(event_df[event_df["label"] == 0][["duration","max_acc"]].describe())
print("\nEvent Label Distribution:")
print(event_df["label"].value_counts())

# =========================
# FEATURE SELECTION
# =========================

features = [
    "max_acc",
    "mean_acc",
    "max_gyro",
    "mean_speed",
    "duration",
    "max_jerk"
]

X = event_df[features]
y = event_df["label"]

# =========================
# TRAIN TEST SPLIT
# =========================

print("\nSplitting dataset...")

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    stratify=y,
    random_state=42
)

# =========================
# MODEL TRAINING
# =========================

print("\nTraining Random Forest model...")

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=12,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# =========================
# MODEL EVALUATION
# =========================

print("\nEvaluating model...")

pred = model.predict(X_test)

print("\nConfusion Matrix:")
print(confusion_matrix(y_test, pred))

print("\nClassification Report:")
print(classification_report(y_test, pred))

# =========================
# SAVE MODEL
# =========================

joblib.dump(model, MODEL_PATH)
print(f"\nModel saved to: {MODEL_PATH}")

print("\nTraining complete.")