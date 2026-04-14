import pandas as pd
import numpy as np
import glob
import os

# CONFIGURATION
SESSIONS_PATH = "../data/sessions/"
OUTPUT_PATH = "../data/processed/combined_sensor_data.csv"

# Create output directory if not exists
os.makedirs("../data/processed/", exist_ok=True)

# Find all session folders
session_folders = [
    f for f in glob.glob(SESSIONS_PATH + "*")
    if os.path.isdir(f)
]

print(f"Found {len(session_folders)} session folders")

all_sessions = []

for folder in session_folders:

    print(f"\nProcessing session: {folder}")

    try:

        acc_file = folder + "/TotalAcceleration.csv"
        gyro_file = folder + "/Gyroscope.csv"
        loc_file = folder + "/Location.csv"
        ori_file = folder + "/Orientation.csv"

        # Check required files exist
        if not os.path.exists(acc_file):
            print("Skipping: No acceleration file")
            continue

        acc = pd.read_csv(acc_file)
        gyro = pd.read_csv(gyro_file) if os.path.exists(gyro_file) else None
        loc = pd.read_csv(loc_file) if os.path.exists(loc_file) else None
        ori = pd.read_csv(ori_file) if os.path.exists(ori_file) else None

        # Rename acceleration
        acc = acc.rename(columns={
            "x": "acc_x",
            "y": "acc_y",
            "z": "acc_z"
        })

        acc = acc[["time", "acc_x", "acc_y", "acc_z"]]

        acc["time"] = pd.to_numeric(acc["time"])
        acc = acc.sort_values("time")

        merged = acc.copy()

        # Merge gyroscope if available
        if gyro is not None:
            gyro = gyro.rename(columns={
                "x": "gyro_x",
                "y": "gyro_y",
                "z": "gyro_z"
            })
            gyro = gyro[["time", "gyro_x", "gyro_y", "gyro_z"]]
            gyro["time"] = pd.to_numeric(gyro["time"])
            gyro = gyro.sort_values("time")

            merged = pd.merge_asof(
                merged, gyro, on="time", direction="nearest"
            )
        else:
            merged["gyro_x"] = 0
            merged["gyro_y"] = 0
            merged["gyro_z"] = 0

        # Merge location if available
        if loc is not None and "speed" in loc.columns:

            loc = loc[["time", "speed", "latitude", "longitude"]]
            loc["time"] = pd.to_numeric(loc["time"])
            loc = loc.sort_values("time")

            merged = pd.merge_asof(
                merged, loc, on="time", direction="nearest"
            )

        else:
            merged["speed"] = 0
            merged["latitude"] = 0
            merged["longitude"] = 0

        # Feature Engineering

        merged["acc_mag"] = np.sqrt(
            merged["acc_x"]**2 +
            merged["acc_y"]**2 +
            merged["acc_z"]**2
        )

        merged["gyro_mag"] = np.sqrt(
            merged["gyro_x"]**2 +
            merged["gyro_y"]**2 +
            merged["gyro_z"]**2
        )

        merged["speed"] = merged["speed"].fillna(0)

        merged["norm_acc"] = merged["acc_mag"] / (
            merged["speed"] + 0.1
        )

        merged["jerk"] = merged["acc_mag"].diff().fillna(0)

        merged["session"] = os.path.basename(folder)

        all_sessions.append(merged)

        print(f"Success: {len(merged)} rows")

    except Exception as e:

        print(f"Error processing {folder}")
        print(e)

# Combine all sessions

if len(all_sessions) == 0:
    print("No valid sessions found")
    exit()

final_data = pd.concat(all_sessions, ignore_index=True)

# Remove invalid values
final_data = final_data.dropna()

# Save
final_data.to_csv(OUTPUT_PATH, index=False)

print("\nSUCCESS")
print(f"Total rows: {len(final_data)}")
print(f"Saved to: {OUTPUT_PATH}")
