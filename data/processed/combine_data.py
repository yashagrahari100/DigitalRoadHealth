import pandas as pd
import glob

# Find all TotalAcceleration.csv files
files = glob.glob("../data/**/TotalAcceleration.csv", recursive=True)

dataframes = []

for file in files:
    df = pd.read_csv(file)
    dataframes.append(df)

# Combine all into one dataset
combined = pd.concat(dataframes, ignore_index=True)

print("Total rows:", len(combined))

combined.to_csv("../data/combined_data.csv", index=False)

print("Combined data saved")
