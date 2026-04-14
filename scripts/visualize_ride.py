import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import os

# Path to your database
DB_PATH = "../backend/potholes.db"

def visualize():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM potholes", conn)
    conn.close()

    if df.empty:
        print("No data found in database.")
        return

    print(f"Found {len(df)} total detections. Plotting...")

    plt.figure(figsize=(12, 8))
    
    # Define colors
    colors = {'pothole': '#EF4444', 'speedbreaker': '#3B82F6'}
    
    # Plot each type
    for label, color in colors.items():
        subset = df[df['anomaly_type'] == label]
        plt.scatter(subset['longitude'], subset['latitude'], 
                    c=color, label=label.title(), 
                    alpha=0.6, edgecolors='w', s=100)

    plt.title('Ride Detection Map (GPS Scatter)', fontsize=15)
    plt.xlabel('Longitude')
    plt.ylabel('Latitude')
    plt.legend()
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Save the plot
    output_path = "ride_map.png"
    plt.savefig(output_path)
    print(f"Success! Visualization saved as: {os.path.abspath(output_path)}")
    plt.show()

if __name__ == "__main__":
    visualize()
