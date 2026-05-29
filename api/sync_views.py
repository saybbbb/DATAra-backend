import os
import csv
import zipfile
import time
import glob
import random
from datetime import datetime, timedelta
from io import BytesIO
from django.http import HttpResponse
from django.conf import settings
from pathlib import Path
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token

# CSV columns mapping
NETWORK_STATS_COLUMNS = [
    "id", "timestamp", "datetime", "hour", "minute", "day_of_week", 
    "is_weekend", "time_period", "bytes_rx", "bytes_tx", "bytes_total", 
    "mb_used", "cumulative_mb_today", "network_type", "screen_on", 
    "battery_level", "device_id", "signal_strength", "is_charging", "device_model"
]

TRAFFIC_STATS_COLUMNS = [
    "id", "timestamp", "datetime", "device_id", "package_name", 
    "app_name", "uid", "bytes_rx", "bytes_tx", "bytes_total", 
    "network_type", "is_system_app"
]

def get_user_datasets_dir(user_id):
    """Returns local dataset directory path for the user."""
    path = Path(settings.BASE_DIR) / 'api' / 'local_datasets' / f'user_{user_id}'
    path.mkdir(parents=True, exist_ok=True)
    return path

def get_global_uploads_dir():
    """Returns the dedicated global uploads folder in the CSV directory."""
    # BASE_DIR is DATAra-backend, parent is DATAra
    path = Path(settings.BASE_DIR).parent / 'CSV' / 'uploaded_datasets'
    path.mkdir(parents=True, exist_ok=True)
    return path

def append_to_csv(filepath, columns, rows):
    """Appends rows to a CSV file, creating it with headers if it doesn't exist."""
    file_exists = os.path.exists(filepath)
    with open(filepath, 'a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(columns)
        for r in rows:
            writer.writerow([r.get(col, '') for col in columns])

def count_csv_records(filepath):
    """Returns the number of data records in a CSV file (excluding header)."""
    if not os.path.exists(filepath):
        return 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header is None:
                return 0
            return sum(1 for row in reader)
    except Exception:
        return 0

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def local_stats_status(request):
    """
    GET — Check how many records have been collected locally for the user
    """
    user_id = request.user.id
    user_dir = get_user_datasets_dir(user_id)
    
    net_path = user_dir / 'network_stats.csv'
    traf_path = user_dir / 'traffic_stats.csv'
    
    return Response({
        "network_records_count": count_csv_records(net_path),
        "traffic_records_count": count_csv_records(traf_path)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def record_local_stats(request):
    """
    POST — Receives local stats from mobile client and appends them to local CSVs
    """
    user_id = request.user.id
    user_dir = get_user_datasets_dir(user_id)
    
    network_stats = request.data.get('network_stats', [])
    traffic_stats = request.data.get('traffic_stats', [])
    
    net_path = user_dir / 'network_stats.csv'
    traf_path = user_dir / 'traffic_stats.csv'
    
    if network_stats:
        append_to_csv(net_path, NETWORK_STATS_COLUMNS, network_stats)
    if traffic_stats:
        append_to_csv(traf_path, TRAFFIC_STATS_COLUMNS, traffic_stats)
        
    return Response({
        "message": "Local statistics recorded successfully.",
        "network_records_count": count_csv_records(net_path),
        "traffic_records_count": count_csv_records(traf_path)
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_to_global(request):
    """
    POST — Copy user local dataset files into the global CSV uploads subfolder
    """
    user_id = request.user.id
    user_dir = get_user_datasets_dir(user_id)
    
    net_path = user_dir / 'network_stats.csv'
    traf_path = user_dir / 'traffic_stats.csv'
    
    if not net_path.exists() and not traf_path.exists():
        return Response(
            {"error": "No local statistics exist to upload. Please generate or record stats first."},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    global_dir = get_global_uploads_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    uploaded_files = []
    
    # Upload NetworkStats
    if net_path.exists() and count_csv_records(net_path) > 0:
        global_net_name = f"data_harvest_user_{user_id}_{timestamp}.csv"
        global_net_path = global_dir / global_net_name
        import shutil
        shutil.copy(net_path, global_net_path)
        uploaded_files.append(global_net_name)
        
    # Upload TrafficStats
    if traf_path.exists() and count_csv_records(traf_path) > 0:
        global_traf_name = f"app_usage_user_{user_id}_{timestamp}.csv"
        global_traf_path = global_dir / global_traf_name
        import shutil
        shutil.copy(traf_path, global_traf_path)
        uploaded_files.append(global_traf_name)
        
    if not uploaded_files:
        return Response(
            {"error": "No records found in local datasets to upload."},
            status=status.HTTP_400_BAD_REQUEST
        )
        
    return Response({
        "message": "Datasets successfully uploaded to the global repository.",
        "folder": "CSV/uploaded_datasets/",
        "files_uploaded": uploaded_files
    })

@api_view(['GET'])
@permission_classes([AllowAny])
def download_local_data(request):
    """
    GET — Packages user's local network and traffic CSVs into a ZIP archive and serves it
    """
    # Authenticate manually (header or query param)
    token_key = request.GET.get('token')
    if not token_key:
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Token '):
            token_key = auth_header.split(' ')[1]
            
    if not token_key:
        return Response({"error": "Authentication token required."}, status=status.HTTP_401_UNAUTHORIZED)
        
    try:
        token = Token.objects.select_related('user').get(key=token_key)
        user = token.user
    except Token.DoesNotExist:
        return Response({"error": "Invalid or expired authentication token."}, status=status.HTTP_401_UNAUTHORIZED)
        
    user_id = user.id
    user_dir = get_user_datasets_dir(user_id)
    
    net_path = user_dir / 'network_stats.csv'
    traf_path = user_dir / 'traffic_stats.csv'
    
    if not net_path.exists() and not traf_path.exists():
        return Response(
            {"error": "No local datasets exist to download. Please generate or record stats first."},
            status=status.HTTP_404_NOT_FOUND
        )
        
    # Create in-memory zip
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        if net_path.exists():
            zip_file.write(net_path, arcname='network_stats.csv')
        if traf_path.exists():
            zip_file.write(traf_path, arcname='traffic_stats.csv')
            
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=datara_user_{user_id}_data.zip'
    return response

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_mock_stats(request):
    """
    POST — Generates synthetic records representing network and app usage stats for testing
    """
    user_id = request.user.id
    user_dir = get_user_datasets_dir(user_id)
    
    net_path = user_dir / 'network_stats.csv'
    traf_path = user_dir / 'traffic_stats.csv'
    
    # Generate 15 Network stats (hourly records)
    mock_net_records = []
    base_time = datetime.now() - timedelta(days=2)
    device_id = "mock-device-uuid-12345"
    device_model = "Mock Simulator X"
    
    apps_pool = [
        {"package": "com.facebook.katana", "name": "Facebook", "uid": 10245},
        {"package": "com.instagram.android", "name": "Instagram", "uid": 10246},
        {"package": "com.google.android.youtube", "name": "YouTube", "uid": 10101},
        {"package": "com.spotify.music", "name": "Spotify", "uid": 10299},
        {"package": "com.tencent.ig", "name": "PUBG Mobile", "uid": 10352}
    ]
    
    mock_traf_records = []
    
    for i in range(15):
        sim_time = base_time + timedelta(hours=i * 3)
        timestamp = int(sim_time.timestamp() * 1000)
        hour = sim_time.hour
        day_of_week = sim_time.isoweekday()
        is_weekend = 1 if day_of_week >= 6 else 0
        time_period = "Night" if hour < 6 else "Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening"
        
        # Network stats record
        mb_used = random.uniform(5.0, 150.0)
        mock_net_records.append({
            "id": random.randint(1000, 9999),
            "timestamp": timestamp,
            "datetime": sim_time.isoformat(),
            "hour": hour,
            "minute": sim_time.minute,
            "day_of_week": day_of_week,
            "is_weekend": is_weekend,
            "time_period": time_period,
            "bytes_rx": int(mb_used * 0.8 * 1024 * 1024),
            "bytes_tx": int(mb_used * 0.2 * 1024 * 1024),
            "bytes_total": int(mb_used * 1024 * 1024),
            "mb_used": mb_used,
            "cumulative_mb_today": mb_used * 1.5,
            "network_type": random.choice(["WIFI", "LTE", "5G"]),
            "screen_on": random.choice([0, 1]),
            "battery_level": max(5, 100 - i * 5),
            "device_id": device_id,
            "signal_strength": random.randint(-110, -60),
            "is_charging": random.choice([0, 0, 0, 1]),
            "device_model": device_model
        })
        
        # Generate 2-3 app usage records for each timestamp
        for app in random.sample(apps_pool, random.randint(2, 4)):
            app_mb = random.uniform(1.0, 60.0)
            mock_traf_records.append({
                "id": random.randint(10000, 99999),
                "timestamp": timestamp,
                "datetime": sim_time.isoformat(),
                "device_id": device_id,
                "package_name": app["package"],
                "app_name": app["name"],
                "uid": app["uid"],
                "bytes_rx": int(app_mb * 0.85 * 1024 * 1024),
                "bytes_tx": int(app_mb * 0.15 * 1024 * 1024),
                "bytes_total": int(app_mb * 1024 * 1024),
                "network_type": random.choice(["MOBILE", "WIFI"]),
                "is_system_app": 0
            })
            
    append_to_csv(net_path, NETWORK_STATS_COLUMNS, mock_net_records)
    append_to_csv(traf_path, TRAFFIC_STATS_COLUMNS, mock_traf_records)
    
    return Response({
        "message": "Synthetic/Mock data generated successfully.",
        "network_records_added": len(mock_net_records),
        "traffic_records_added": len(mock_traf_records),
        "total_local_network_records": count_csv_records(net_path),
        "total_local_traffic_records": count_csv_records(traf_path)
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def global_averages(request):
    """
    GET — Parses the global app_usage*.csv files and calculates average consumption per application
    """
    csv_dir = Path(settings.BASE_DIR).parent / 'CSV'
    
    csv_files = glob.glob(str(csv_dir / "app_usage*.csv"))
    
    app_totals = {}
    app_counts = {}
    
    for f in csv_files:
        try:
            with open(f, 'r', encoding='utf-8') as cf:
                reader = csv.DictReader(cf)
                for row in reader:
                    app_name = row.get('app_name')
                    bytes_total = row.get('bytes_total')
                    
                    if app_name and bytes_total:
                        try:
                            mb = float(bytes_total) / (1024.0 * 1024.0)
                            app_totals[app_name] = app_totals.get(app_name, 0.0) + mb
                            app_counts[app_name] = app_counts.get(app_name, 0) + 1
                        except ValueError:
                            continue
        except Exception as e:
            continue
            
    # Calculate average
    averages = []
    for app_name, total_mb in app_totals.items():
        count = app_counts[app_name]
        avg_mb = total_mb / count if count > 0 else 0
        averages.append({
            "app_name": app_name,
            "average_consumption_mb": round(avg_mb, 2),
            "data_points": count
        })
        
    # Sort by average consumption descending
    averages = sorted(averages, key=lambda x: x["average_consumption_mb"], reverse=True)
    
    return Response({
        "baseline_average_user_consumption": averages[:10]  # top 10 apps
    })
