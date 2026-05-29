import os
import glob
import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import joblib

def train_data_usage_model():
    # Define paths
    base_dir = Path(__file__).resolve().parent.parent
    csv_dir = base_dir.parent / 'CSV'
    model_dir = base_dir / 'api' / 'ml_models'
    
    # Create model output directory if it doesn't exist
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Searching for data harvest CSV files in: {csv_dir}")
    csv_files = glob.glob(str(csv_dir / "data_harvest*.csv"))
    
    if not csv_files:
        raise FileNotFoundError(f"No data_harvest*.csv files found in {csv_dir}")
        
    print(f"Found {len(csv_files)} CSV files to process.")
    
    # Load and combine all data harvest files
    dfs = []
    for f in csv_files:
        try:
            df_temp = pd.read_csv(f)
            dfs.append(df_temp)
            print(f"Loaded {f} with {len(df_temp)} rows.")
        except Exception as e:
            print(f"Error loading {f}: {e}")
            
    if not dfs:
        raise ValueError("No data could be loaded.")
        
    df = pd.concat(dfs, ignore_index=True)
    print(f"Total raw rows: {len(df)}")
    
    # Preprocessing
    # Ensure datetime format and correct types
    df['datetime'] = pd.to_datetime(df['datetime'])
    df['hour'] = df['datetime'].dt.hour
    
    # We want to train on cellular usage specifically if possible, as that consumes the data plan
    # If network_type column exists, check its values
    if 'network_type' in df.columns:
        print("Network types in dataset:")
        print(df['network_type'].value_counts())
        
        # Filter for cellular/mobile usage, but fall back if it is too small
        cellular_df = df[df['network_type'].isin(['CELLULAR', 'MOBILE'])]
        if len(cellular_df) > 100:
            df = cellular_df
            print(f"Filtered for Cellular data usage. Rows remaining: {len(df)}")
        else:
            print("Cellular data count too low, using all network types.")
            
    # Define date column for aggregation
    df['date'] = df['datetime'].dt.date
    
    # Aggregate to hourly intervals
    # We want sum of mb_used, and mean of screen_on/battery_level per hour
    agg_dict = {'mb_used': 'sum'}
    if 'screen_on' in df.columns:
        agg_dict['screen_on'] = 'mean'
    if 'battery_level' in df.columns:
        agg_dict['battery_level'] = 'mean'
        
    hourly_df = df.groupby(['date', 'hour', 'day_of_week', 'is_weekend']).agg(agg_dict).reset_index()
    print(f"Aggregated to {len(hourly_df)} hourly usage records.")
    
    # Feature engineering / selections
    features = ['hour', 'day_of_week', 'is_weekend']
    if 'screen_on' in hourly_df.columns:
        # Fill NaNs in screen_on (often 0 or mean)
        hourly_df['screen_on'] = hourly_df['screen_on'].fillna(0.0)
        features.append('screen_on')
    if 'battery_level' in hourly_df.columns:
        hourly_df['battery_level'] = hourly_df['battery_level'].fillna(50.0)
        features.append('battery_level')
        
    X = hourly_df[features]
    y = hourly_df['mb_used']
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train RandomForest model
    print(f"Training Random Forest Regressor using features: {features}")
    model = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
    model.fit(X_train, y_train)
    
    # Evaluate model
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    mse = mean_squared_error(y_test, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_test, y_pred)
    
    print("\n--- Evaluation Metrics ---")
    print(f"Mean Absolute Error (MAE): {mae:.4f} MB")
    print(f"Root Mean Squared Error (RMSE): {rmse:.4f} MB")
    print(f"R-squared (R2 Score): {r2:.4f}")
    
    # Save model and feature list
    model_path = model_dir / 'data_depletion_model.joblib'
    model_data = {
        'model': model,
        'features': features,
        'aggregated_hourly_mean': float(y_train.mean()) # fallback prediction
    }
    joblib.dump(model_data, model_path)
    print(f"Model saved successfully to {model_path}")
    
    # Save metrics JSON
    metrics = {
        'mae_mb': float(mae),
        'rmse_mb': float(rmse),
        'r2_score': float(r2),
        'features_used': features,
        'dataset_size_records': int(len(hourly_df))
    }
    metrics_path = model_dir / 'metrics.json'
    with open(metrics_path, 'w') as mf:
        json.dump(metrics, mf, indent=4)
    print(f"Metrics saved to {metrics_path}")

if __name__ == '__main__':
    train_data_usage_model()
