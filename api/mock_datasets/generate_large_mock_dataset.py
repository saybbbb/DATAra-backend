import os
import csv
import datetime
import random
from pathlib import Path

def generate_large_mock_datasets():
    # Define paths
    base_dir = Path(__file__).resolve().parent.parent.parent
    backend_mock_dir = base_dir / 'api' / 'mock_datasets'
    global_csv_dir = base_dir.parent / 'CSV'
    
    # Ensure directories exist
    backend_mock_dir.mkdir(parents=True, exist_ok=True)
    global_csv_dir.mkdir(parents=True, exist_ok=True)
    
    net_backend_path = backend_mock_dir / 'data_harvest_mock_large.csv'
    net_global_path = global_csv_dir / 'data_harvest_mock_large.csv'
    
    app_backend_path = backend_mock_dir / 'app_usage_mock_large.csv'
    app_global_path = global_csv_dir / 'app_usage_mock_large.csv'
    
    print("Generating NetworkStats (NetworkstatManager) mock dataset...")
    
    net_columns = [
        "id", "timestamp", "datetime", "hour", "minute", "day_of_week", 
        "is_weekend", "time_period", "bytes_rx", "bytes_tx", "bytes_total", 
        "mb_used", "cumulative_mb_today", "network_type", "screen_on", "battery_level"
    ]
    
    app_columns = [
        "id", "timestamp", "datetime", "device_id", "package_name", 
        "app_name", "uid", "bytes_rx", "bytes_tx", "bytes_total", 
        "network_type", "is_system_app"
    ]
    
    # Generate data spanning 60 days
    start_date = datetime.datetime(2026, 4, 1, 0, 0, 0)
    total_hours = 60 * 24 # 1440 hours
    
    net_rows = []
    app_rows = []
    
    device_id = "mock-device-uuid-12345"
    apps_pool = [
        {"package": "com.facebook.katana", "name": "Facebook", "uid": 10245},
        {"package": "com.instagram.android", "name": "Instagram", "uid": 10246},
        {"package": "com.google.android.youtube", "name": "YouTube", "uid": 10101},
        {"package": "com.spotify.music", "name": "Spotify", "uid": 10299},
        {"package": "com.tencent.ig", "name": "PUBG Mobile", "uid": 10352},
        {"package": "com.android.chrome", "name": "Chrome", "uid": 10080},
        {"package": "com.zhiliaoapp.musically", "name": "TikTok", "uid": 10310}
    ]
    
    app_row_id = 1
    
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
            
        # Simulate screen_on time
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
        if hour == 0:
            battery_level = float(random.randint(95, 100))
        else:
            prev_battery = net_rows[-1]["battery_level"] if net_rows else 100.0
            drain = screen_on * random.uniform(10.0, 18.0) + random.uniform(1.0, 3.0)
            
            if hour <= 6 or hour >= 22:
                battery_level = min(100.0, prev_battery + random.uniform(15.0, 25.0))
            else:
                battery_level = max(3.0, prev_battery - drain)
                
        battery_level = round(battery_level, 1)
        
        # Simulate dynamic cellular usage
        base_mb = 120.0 * screen_on
        if hour in [18, 19, 20, 21, 22]:
            base_mb += random.uniform(50.0, 150.0)
        if is_weekend:
            base_mb += random.uniform(10.0, 40.0)
            
        mb_used = max(0.0, base_mb + random.uniform(-15.0, 15.0))
        mb_used = round(mb_used, 4)
        
        bytes_total = int(mb_used * 1024 * 1024)
        bytes_rx = int(bytes_total * random.uniform(0.75, 0.90))
        bytes_tx = bytes_total - bytes_rx
        
        # Cumulative today (resets at hour 0)
        if hour == 0:
            cumulative_mb_today = mb_used
        else:
            prev_cum = net_rows[-1]["cumulative_mb_today"] if net_rows else 0.0
            if sim_time.date() == (sim_time - datetime.timedelta(hours=1)).date():
                cumulative_mb_today = prev_cum + mb_used
            else:
                cumulative_mb_today = mb_used
                
        cumulative_mb_today = round(cumulative_mb_today, 4)
        
        net_rows.append({
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
        
        # Generate TrafficStats app records for this hour
        # Select 2 to 4 random apps that were active
        num_apps = random.randint(2, 5)
        active_apps = random.sample(apps_pool, num_apps)
        
        # Split total mb_used among these active apps
        remaining_app_mb = mb_used
        for idx, app in enumerate(active_apps):
            if idx == len(active_apps) - 1:
                app_mb = remaining_app_mb
            else:
                app_mb = random.uniform(0.05, 0.70) * remaining_app_mb
                remaining_app_mb -= app_mb
                
            app_bytes_total = int(app_mb * 1024 * 1024)
            app_bytes_rx = int(app_bytes_total * random.uniform(0.80, 0.95))
            app_bytes_tx = app_bytes_total - app_bytes_rx
            
            app_rows.append({
                "id": app_row_id,
                "timestamp": timestamp,
                "datetime": sim_time.isoformat(),
                "device_id": device_id,
                "package_name": app["package"],
                "app_name": app["name"],
                "uid": app["uid"],
                "bytes_rx": app_bytes_rx,
                "bytes_tx": app_bytes_tx,
                "bytes_total": app_bytes_total,
                "network_type": "MOBILE",
                "is_system_app": 0
            })
            app_row_id += 1
            
    # Write NetworkStats
    for path in [net_backend_path, net_global_path]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(net_columns)
            for r in net_rows:
                writer.writerow([r[col] for col in net_columns])
        print(f"Saved NetworkStats dataset with {len(net_rows)} rows to {path}")
        
    # Write TrafficStats
    for path in [app_backend_path, app_global_path]:
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(app_columns)
            for r in app_rows:
                writer.writerow([r[col] for col in app_columns])
        print(f"Saved TrafficStats dataset with {len(app_rows)} rows to {path}")

if __name__ == '__main__':
    generate_large_mock_datasets()
