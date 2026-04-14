import sqlite3
import pandas as pd
import folium
import os
from folium.plugins import MarkerCluster

# Path to your database
DB_PATH = "../backend/potholes.db"
OUTPUT_MAP = "interactive_road_map.html"

def create_interactive_map():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM potholes", conn)
    conn.close()

    if df.empty:
        print("No data found in database.")
        return

    # Center map on the average location
    start_lat = df['latitude'].mean()
    start_lon = df['longitude'].mean()
    
    # Create the map using OpenStreetMap
    m = folium.Map(location=[start_lat, start_lon], zoom_start=15, tiles="OpenStreetMap")

    marker_cluster = MarkerCluster().add_to(m)

    # Add markers
    for _, row in df.iterrows():
        color = 'red' if row['anomaly_type'] == 'pothole' else 'blue'
        icon = 'exclamation-triangle' if row['anomaly_type'] == 'pothole' else 'road'
        
        popup_text = f"<b>Type:</b> {row['anomaly_type'].title()}<br>" \
                     f"<b>Severity:</b> {row['severity']}<br>" \
                     f"<b>Reports:</b> {row['report_count']}<br>" \
                     f"<b>Time:</b> {row['timestamp']}"
        
        folium.Marker(
            location=[row['latitude'], row['longitude']],
            popup=folium.Popup(popup_text, max_width=300),
            tooltip=f"{row['anomaly_type'].title()} ({row['severity']})",
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(marker_cluster)

    # Save the map
    m.save(OUTPUT_MAP)
    print(f"Success! Interactive map saved as: {os.path.abspath(OUTPUT_MAP)}")
    print("Open this file in your browser to view the map.")

if __name__ == "__main__":
    create_interactive_map()
