import pandas as pd
import numpy as np
import joblib
import os
import folium


# =========================
# CONFIG
# =========================

MODEL_PATH = "../model/pothole_model.pkl"
SESSION_PATH = "../data/sessions/Camp/"   # CHANGE THIS

SPIKE_THRESHOLD = 18

# =========================
# LOAD MODEL
# =========================

print("Loading trained model...")
model = joblib.load(MODEL_PATH)

# =========================
# LOAD NEW SESSION DATA
# =========================

print("Loading new session data...")

acc = pd.read_csv(SESSION_PATH + "TotalAcceleration.csv")
gyro = pd.read_csv(SESSION_PATH + "Gyroscope.csv")
loc = pd.read_csv(SESSION_PATH + "Location.csv")

# Rename columns if needed
acc = acc.rename(columns={"x": "acc_x", "y": "acc_y", "z": "acc_z"})
gyro = gyro.rename(columns={"x": "gyro_x", "y": "gyro_y", "z": "gyro_z"})

# Convert time to numeric
acc["time"] = pd.to_numeric(acc["time"])
gyro["time"] = pd.to_numeric(gyro["time"])
loc["time"] = pd.to_numeric(loc["time"])

# Sort
acc = acc.sort_values("time")
gyro = gyro.sort_values("time")
loc = loc.sort_values("time")

# Merge
data = pd.merge_asof(acc, gyro, on="time")
data = pd.merge_asof(data, loc, on="time")

# =========================
# CREATE BASIC FEATURES
# =========================

data["acc_mag"] = np.sqrt(
    data["acc_x"]**2 +
    data["acc_y"]**2 +
    data["acc_z"]**2
)

data["gyro_mag"] = np.sqrt(
    data["gyro_x"]**2 +
    data["gyro_y"]**2 +
    data["gyro_z"]**2
)

data["jerk"] = data["acc_mag"].diff().fillna(0)
data["speed"] = data["speed"].fillna(0)

# =========================
# ESTIMATE SAMPLING RATE
# =========================

time_diff = data["time"].diff().median()
sampling_rate = 1e9 / time_diff if time_diff > 0 else 50

print(f"Estimated sampling rate: {sampling_rate:.2f} Hz")

# =========================
# DETECT SPIKE EVENTS
# =========================

data["is_spike"] = data["acc_mag"] > SPIKE_THRESHOLD
data["spike_group"] = (
    data["is_spike"] != data["is_spike"].shift()
).cumsum()

event_rows = []
event_locations = []

for group_id, group in data.groupby("spike_group"):

    if not group["is_spike"].iloc[0]:
        continue

    duration = len(group) / sampling_rate
    max_acc = group["acc_mag"].max()
    mean_acc = group["acc_mag"].mean()
    max_gyro = group["gyro_mag"].max()
    mean_speed = group["speed"].mean()
    max_jerk = group["jerk"].abs().max()

    # Save representative GPS (middle of event)
    mid_row = group.iloc[len(group)//2]

    event_rows.append([
        max_acc,
        mean_acc,
        max_gyro,
        mean_speed,
        duration,
        max_jerk
    ])

    event_locations.append([
        mid_row["latitude"],
        mid_row["longitude"]
    ])

event_df = pd.DataFrame(event_rows, columns=[
    "max_acc",
    "mean_acc",
    "max_gyro",
    "mean_speed",
    "duration",
    "max_jerk"
])

print(f"Total spike events in new session: {len(event_df)}")

# =========================
# PREDICT
# =========================

predictions = model.predict(event_df)

event_df["prediction"] = predictions

# Attach GPS
event_df["latitude"] = [loc[0] for loc in event_locations]
event_df["longitude"] = [loc[1] for loc in event_locations]

# =========================
# RESULTS
# =========================

potholes = event_df[event_df["prediction"] == 1]

print(f"\nDetected pothole events: {len(potholes)}")

print("\nSample detections:")
print(potholes.head())

print("\nTesting complete.")


print("Generating map...")

# Create base map centered on first pothole
if len(potholes) > 0:
    center_lat = potholes.iloc[0]["latitude"]
    center_lon = potholes.iloc[0]["longitude"]
else:
    center_lat = event_df.iloc[0]["latitude"]
    center_lon = event_df.iloc[0]["longitude"]

m = folium.Map(location=[center_lat, center_lon], zoom_start=16)

# Add pothole markers
for _, row in potholes.iterrows():

    folium.CircleMarker(
        location=[row["latitude"], row["longitude"]],
        radius=6,
        color="red",
        fill=True,
        fill_color="red",
        fill_opacity=0.7,
        popup=(
            f"Max Acc: {row['max_acc']:.2f}<br>"
            f"Duration: {row['duration']:.3f}s"
        )
    ).add_to(m)

# Save map
map_file = "new_session_potholes_map.html"
m.save(map_file)

print(f"Map saved as {map_file}")