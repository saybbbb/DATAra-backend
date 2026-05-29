import os
import csv
import datetime
import random
from pathlib import Path

def generate_large_mock_dataset():
    # Define paths
    base_dir = Path(__file__).resolve().parent.parent.parent
    backend_mock_dir = base_dir / 'api' / 'mock_datasets'
    global_csv_dir = base_dir.parent / 'CSV'
    
    # Ensure directories exist
    backend_mock_dir.mkdir(parents=True, exist_ok=True)
    global_csv_dir.mkdir(parents=True, exist_ok=True)
    
    backend_csv_path = backend_mock_dir / 'data_harvest_mock_large.csv'
    global_csv_path = global_csv_dir / 'data_harvest_mock_large.csv'
    
    print(f"Generating mock dataset...")
    
    columns = [
        "id", "timestamp", "datetime", "hour", "minute", "day_of_week", 
        "is_weekend", "time_period", "bytes_rx", "bytes_tx", "bytes_total", 
        "mb_used", "cumulative_mb_today", "network_type", "screen_on", "battery_level"
    ]
    
    # Generate data spanning 60 days
    start_date = datetime.datetime(2026, 4, 1, 0, 0, 0)
    total_hours = 60 * 24 # 1440 hours
    
    rows = []
    
    for h_offset in range(total_hours):
        sim_time = start_date + datetime.timedelta(hours=h_offset)
        timestamp = int(sim_time.timestamp() * 1000)
        hour = sim_time.hour
        day_of_week = sim_time.isoweekday() # 1=Monday, 7=Sunday
        is_weekend = 1 if day_of_week >= 6 else 0
        
        # Time period label
        if hour < 6:
            time_period = "Night"
        elif hour < 12:
            time_period = "Morning"
        elif hour < 18:
            time_period = "Afternoon"
        else:
            time_period = "Evening"
            
        # Simulate realistic screen_on time (percentage of hour active)
        # Night: low, Evening/Weekend: high, daytime: moderate
        if time_period == "Night":
            base_screen = random.uniform(0.01, 0.10)
        elif time_period == "Evening":
            base_screen = random.uniform(0.50, 0.90)
        else:
            base_screen = random.uniform(0.20, 0.60)
            
        if is_weekend:
            base_screen = min(1.0, base_screen + random.uniform(0.05, 0.20))
            
        screen_on = round(base_screen, 3)
        
        # Simulate battery level
        # Day starts full and drains, charging cycles at night/office hours
        if hour == 0:
            battery_level = float(random.randint(95, 100))
        else:
            prev_battery = rows[-1]["battery_level"] if rows else 100.0
            # drain is proportional to screen_on
            drain = screen_on * random.uniform(10.0, 18.0) + random.uniform(1.0, 3.0)
            
            # Simple charge logic: charging at night (0-6) or evening (22-23)
            if hour <= 6 or hour >= 22:
                battery_level = min(100.0, prev_battery + random.uniform(15.0, 25.0))
            else:
                battery_level = max(3.0, prev_battery - drain)
                
        battery_level = round(battery_level, 1)
        
        # Simulate highly predictive cellular data usage (mb_used)
        # We make it heavily correlated with screen_on, hour, and weekend
        # So that machine learning models (XGBoost, Random Forest) can capture it easily
        base_mb = 120.0 * screen_on # screen activity consumes data
        
        # Add peak hours surge (e.g., video streaming in evening)
        if hour in [18, 19, 20, 21, 22]:
            base_mb += random.uniform(50.0, 150.0)
            
        # Add weekend boost
        if is_weekend:
            base_mb += random.uniform(10.0, 40.0)
            
        # Add noise
        mb_used = max(0.0, base_mb + random.uniform(-15.0, 15.0))
        mb_used = round(mb_used, 4)
        
        # Bytes translation
        bytes_total = int(mb_used * 1024 * 1024)
        bytes_rx = int(bytes_total * random.uniform(0.75, 0.90))
        bytes_tx = bytes_total - bytes_rx
        
        # Cumulative today (resets at hour 0)
        if hour == 0:
            cumulative_mb_today = mb_used
        else:
            prev_cum = rows[-1]["cumulative_mb_today"] if rows else 0.0
            # check if previous row belongs to the same day
            if sim_time.date() == (sim_time - datetime.timedelta(hours=1)).date():
                cumulative_mb_today = prev_cum + mb_used
            else:
                cumulative_mb_today = mb_used
                
        cumulative_mb_today = round(cumulative_mb_today, 4)
        
        rows.append({
            "id": h_offset + 1,
            "timestamp": timestamp,
            "datetime": sim_time.isoformat(),
            "hour": hour,
            "minute": random.randint(0, 59),
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "time_period": time_period,
            "bytes_rx": bytes_rx,
            "bytes_tx": bytes_tx,
            "bytes_total": bytes_total,
            "mb_used": mb_used,
            "cumulative_mb_today": cumulative_mb_today,
            "network_type": "CELLULAR",
            "screen_on": screen_on,
            "battery_level": battery_level
        })
        
    # Write to files
    for path in [backend_csv_path, global_csv_path]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for r in rows:
                writer.writerow([r[col] for col in columns])
        print(f"Saved dataset with {len(rows)} rows to {path}")

if __name__ == '__main__':
    generate_large_mock_dataset()
