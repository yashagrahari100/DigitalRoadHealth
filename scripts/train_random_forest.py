import os
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import matplotlib.pyplot as plt
import seaborn as sns

# Constants
WINDOW_SIZE_SEC = 1.5
STEP_SIZE_SEC = 0.5 # For overlapping
ANOMALY_WINDOW_PADDING = 1.0 # 1 second before and after the annotation click is considered part of the anomaly event

def load_session_data(base_path, session_name):
    """Loads and merges Accelerometer, Gyroscope, and Annotation data for a session."""
    session_path = os.path.join(base_path, session_name)
    
    acc_df = pd.read_csv(os.path.join(session_path, 'Accelerometer.csv'))
    gyr_df = pd.read_csv(os.path.join(session_path, 'Gyroscope.csv'))
    
    # Merge accel and gyro on closest time or seconds_elapsed
    # Both sets are typically sampled similarly, but interpolation ensures alignment
    df = pd.merge_asof(
        acc_df.sort_values('time'),
        gyr_df.sort_values('time'),
        on='time', suffixes=('_acc', '_gyr'),
        direction='nearest'
    )
    
    # Read annotations
    ann_df = pd.read_csv(os.path.join(session_path, 'Annotation.csv'))
    
    return df, ann_df

def extract_features(window_df):
    """Extracts statistical features from a 1.5-second sliding window."""
    # Magnitudes
    window_df = window_df.copy()
    window_df['acc_mag'] = np.sqrt(window_df['x_acc']**2 + window_df['y_acc']**2 + window_df['z_acc']**2)
    window_df['gyr_mag'] = np.sqrt(window_df['x_gyr']**2 + window_df['y_gyr']**2 + window_df['z_gyr']**2)

    features = {}
    
    # Accelerometer Magnitude features
    features['acc_mean'] = window_df['acc_mag'].mean()
    features['acc_max'] = window_df['acc_mag'].max()
    features['acc_min'] = window_df['acc_mag'].min()
    features['acc_std'] = window_df['acc_mag'].std()
    features['acc_jerk'] = features['acc_max'] - features['acc_min']
    
    # Gyroscope Magnitude features
    features['gyr_mean'] = window_df['gyr_mag'].mean()
    features['gyr_max'] = window_df['gyr_mag'].max()
    features['gyr_min'] = window_df['gyr_mag'].min()
    features['gyr_std'] = window_df['gyr_mag'].std()
    features['gyr_jerk'] = features['gyr_max'] - features['gyr_min']

    return features

def determine_label(window_time, ann_df):
    """Determines the class label for a given window centered at window_time."""
    # Find annotations near this time window (+/- ANOMALY_WINDOW_PADDING)
    close_anns = ann_df[np.abs(ann_df['seconds_elapsed'] - window_time) <= ANOMALY_WINDOW_PADDING]
    
    if len(close_anns) > 0:
        # Prioritize Speed Breaker if overlapping, otherwise Pothole
        labels = close_anns['text'].str.lower().values
        if any('speed breaker' in l or 'speedbreaker' in l for l in labels):
            return 'speedbreaker'
        return 'pothole'
    
    # Normal road requires strict isolation
    too_close_anns = ann_df[np.abs(ann_df['seconds_elapsed'] - window_time) <= (ANOMALY_WINDOW_PADDING + 2.0)]
    if len(too_close_anns) == 0:
        return 'normal_road'
    
    return 'ignore' # Too close to anomaly boundary, vague signal, ignore this window

def process_session(base_path, session_name):
    print(f"Processing session: {session_name}...")
    df, ann_df = load_session_data(base_path, session_name)
    
    X = []
    y = []
    
    # Create overlapping windows using sliding step
    max_time = df['seconds_elapsed_acc'].max()
    current_time = df['seconds_elapsed_acc'].min()
    
    while current_time + WINDOW_SIZE_SEC <= max_time:
        window_mask = (df['seconds_elapsed_acc'] >= current_time) & (df['seconds_elapsed_acc'] < current_time + WINDOW_SIZE_SEC)
        window_df = df[window_mask]
        
        # Center of the window
        center_time = current_time + (WINDOW_SIZE_SEC / 2.0)
        label = determine_label(center_time, ann_df)
        
        if label != 'ignore' and len(window_df) > 10: # Ensure valid window size
            features = extract_features(window_df)
            X.append(features)
            y.append(label)
            
        current_time += STEP_SIZE_SEC
        
    return pd.DataFrame(X), np.array(y)

def main():
    base_path = "data/sessions"
    sessions = ['Camp', 'Peth'] # Strict use of manually labeled data only
    
    all_X = []
    all_y = []
    
    for session in sessions:
        if os.path.exists(os.path.join(base_path, session)):
            X, y = process_session(base_path, session)
            all_X.append(X)
            all_y.extend(y)
        else:
            print(f"Session {session} not found in {base_path}!")

    if not all_X:
        print("No valid data found to train.")
        return

    X_df = pd.concat(all_X, ignore_index=True)
    y_arr = np.array(all_y)
    
    # --- Class Balancing ---
    print("\nOriginal class distribution:")
    unique, counts = np.unique(y_arr, return_counts=True)
    print(dict(zip(unique, counts)))
    
    # Downsample normal_road to ~match anomaly sum to prevent vast bias
    anomaly_count = sum(y_arr == 'pothole') + sum(y_arr == 'speedbreaker')
    normal_idx = np.where(y_arr == 'normal_road')[0]
    pothole_idx = np.where(y_arr == 'pothole')[0]
    speedbreaker_idx = np.where(y_arr == 'speedbreaker')[0]
    
    # Optional SMOTE vs Simple Duplication oversampling can be done here. 
    # For robust mobile prediction, duplicating minority to balance is safe if very scarce.
    # We will downsample normal_road heavily to retain pattern purity vs frequency dominance.
    if len(normal_idx) > max(len(pothole_idx), len(speedbreaker_idx)):
        # Randomly sample normal_road to 2x the max anomaly class to provide a solid baseline
        target_normal_size = max(len(pothole_idx), len(speedbreaker_idx)) * 2
        
        # Sometimes dataset might be extremely small, safeguard random choice
        actual_normal_size = min(len(normal_idx), target_normal_size)
    else:
        actual_normal_size = len(normal_idx)

    downsampled_normal_idx = np.random.choice(normal_idx, size=actual_normal_size, replace=False)
    
    balanced_idx = np.concatenate([pothole_idx, speedbreaker_idx, downsampled_normal_idx])
    np.random.shuffle(balanced_idx)
    
    X_balanced = X_df.iloc[balanced_idx]
    y_balanced = y_arr[balanced_idx]
    
    print("\nBalanced class distribution:")
    unique, counts = np.unique(y_balanced, return_counts=True)
    print(dict(zip(unique, counts)))

    # --- Training ---
    X_train, X_test, y_train, y_test = train_test_split(X_balanced, y_balanced, test_size=0.2, random_state=42, stratify=y_balanced)
    
    print("\nTraining Random Forest Classifier...")
    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, class_weight='balanced')
    model.fit(X_train, y_train)
    
    # --- Evaluation ---
    y_pred = model.predict(X_test)
    print("\n=== Model Evaluation ===")
    print("Accuracy:", accuracy_score(y_test, y_pred))
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Confusion Matrix Output
    cm = confusion_matrix(y_test, y_pred, labels=model.classes_)
    plt.figure(figsize=(8,6))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', xticklabels=model.classes_, yticklabels=model.classes_)
    plt.title('Confusion Matrix: Random Forest (Camp & Peth)')
    plt.xlabel('Predicted')
    plt.ylabel('Actual')
    plt.tight_layout()
    plt.savefig('confusion_matrix.png')
    print("Saved confusion_matrix.png to workspace.")
    
    # --- Export Model ---
    os.makedirs('backend/app/models', exist_ok=True) # Ensure directory exists
    joblib.dump(model, 'backend/app/models/random_forest_model.pkl')
    # Save the feature names so the API always pushes the schema correctly
    joblib.dump(X_train.columns.tolist(), 'backend/app/models/rf_features.pkl')
    print("Model saved to backend/app/models/random_forest_model.pkl")

if __name__ == "__main__":
    main()
