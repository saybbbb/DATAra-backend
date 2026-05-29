from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import DataUsageRecord, UserProfile
from datetime import date, timedelta, datetime
import random
import os
import csv
from django.conf import settings

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

class Command(BaseCommand):
    help = 'Seeds the database with sample usage records and creates 5 tester mock accounts with local CSV datasets.'

    def generate_local_files(self, user_id):
        user_dir = os.path.join(settings.BASE_DIR, 'api', 'local_datasets', f'user_{user_id}')
        os.makedirs(user_dir, exist_ok=True)
        
        net_path = os.path.join(user_dir, 'network_stats.csv')
        traf_path = os.path.join(user_dir, 'traffic_stats.csv')
        
        # Overwrite/generate fresh network stats
        with open(net_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(NETWORK_STATS_COLUMNS)
            
            base_time = datetime.now() - timedelta(days=5)
            device_id = f"device-uuid-tester-{user_id}"
            device_model = "Tester Simulator Phone"
            cumulative_today = 0.0
            last_day = None
            
            for i in range(50):
                sim_time = base_time + timedelta(hours=i * 2.4)
                day_str = sim_time.date().isoformat()
                if last_day != day_str:
                    cumulative_today = 0.0
                    last_day = day_str
                    
                timestamp = int(sim_time.timestamp() * 1000)
                hour = sim_time.hour
                day_of_week = sim_time.isoweekday()
                is_weekend = 1 if day_of_week >= 6 else 0
                time_period = "Night" if hour < 6 else "Morning" if hour < 12 else "Afternoon" if hour < 18 else "Evening"
                
                mb_used = random.uniform(1.0, 80.0)
                cumulative_today += mb_used
                
                row = [
                    random.randint(1000, 9999),
                    timestamp,
                    sim_time.isoformat(),
                    hour,
                    sim_time.minute,
                    day_of_week,
                    is_weekend,
                    time_period,
                    int(mb_used * 0.85 * 1024 * 1024),
                    int(mb_used * 0.15 * 1024 * 1024),
                    int(mb_used * 1024 * 1024),
                    round(mb_used, 2),
                    round(cumulative_today, 2),
                    random.choice(["WIFI", "LTE", "5G"]),
                    random.choice([0, 1]),
                    max(10, 100 - (i % 20) * 4),
                    device_id,
                    random.randint(-105, -65),
                    random.choice([0, 0, 1]),
                    device_model
                ]
                writer.writerow(row)
                
        # Overwrite/generate traffic stats
        apps_pool = [
            {"package": "com.facebook.katana", "name": "Facebook", "uid": 10245},
            {"package": "com.instagram.android", "name": "Instagram", "uid": 10246},
            {"package": "com.google.android.youtube", "name": "YouTube", "uid": 10101},
            {"package": "com.spotify.music", "name": "Spotify", "uid": 10299},
            {"package": "com.tencent.ig", "name": "PUBG Mobile", "uid": 10352},
            {"package": "com.chrome.android", "name": "Chrome", "uid": 10080}
        ]
        
        with open(traf_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(TRAFFIC_STATS_COLUMNS)
            
            for i in range(100):
                sim_time = base_time + timedelta(hours=i * 1.2)
                timestamp = int(sim_time.timestamp() * 1000)
                app = random.choice(apps_pool)
                app_mb = random.uniform(0.5, 45.0)
                
                row = [
                    random.randint(10000, 99999),
                    timestamp,
                    sim_time.isoformat(),
                    device_id,
                    app["package"],
                    app["name"],
                    app["uid"],
                    int(app_mb * 0.8 * 1024 * 1024),
                    int(app_mb * 0.2 * 1024 * 1024),
                    int(app_mb * 1024 * 1024),
                    random.choice(["MOBILE", "WIFI"]),
                    0
                ]
                writer.writerow(row)

    def handle(self, *args, **kwargs):
        # 1. Seed original database usage records (normal, warning, extreme)
        test_accounts = [
            {
                "phone": "09111111111",
                "name": "Normal Pace",
                "tier": "normal",
                "target_mb_per_slot": (40, 45)
            },
            {
                "phone": "09222222222",
                "name": "Warning Pace",
                "tier": "warning",
                "target_mb_per_slot": (75, 85)
            },
            {
                "phone": "09333333333",
                "name": "Extreme Pace",
                "tier": "extreme",
                "target_mb_per_slot": (90, 105)
            }
        ]

        users_to_seed = []
        for acc in test_accounts:
            user, created = User.objects.get_or_create(username=acc["phone"])
            if created:
                user.set_password("pass1234")
                user.save()
            
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.full_name = acc["name"]
            profile.phone_number = acc["phone"]
            profile.save()
            
            users_to_seed.append((user, acc))

        self.stdout.write('Clearing old DataUsageRecord data...')
        DataUsageRecord.objects.all().delete()
            
        apps = ['Facebook', 'YouTube', 'TikTok', 'Instagram', 'Chrome', 'Netflix', 'Spotify', 'Roblox']
        
        for user, acc in users_to_seed:
            self.stdout.write(f'Seeding database records for {acc["name"]} ({acc["phone"]})')
            for i in range(28):
                current_date = date.today() - timedelta(days=i)
                for j in range(5):
                    hour = random.randint(0, 23)
                    time_slot = f"{hour:02d}:00-{hour+1:02d}:00"
                    min_mb, max_mb = acc["target_mb_per_slot"]
                    app_choice = "Roblox" if acc["tier"] == "extreme" and random.random() < 0.7 else random.choice(apps)
                    
                    DataUsageRecord.objects.create(
                        user=user,
                        date=current_date,
                        time_slot=time_slot,
                        data_used_mb=round(random.uniform(min_mb, max_mb), 2),
                        app_name=app_choice
                    )

        # 2. Seed 5 new mock tester accounts with unique user IDs (101 to 105)
        # Login phone number is 11 digits, password is 8 chars alphanumeric
        tester_accounts = [
            {"id": 101, "phone": "09811111111", "name": "Tester One", "pass": "pass1234"},
            {"id": 102, "phone": "09822222222", "name": "Tester Two", "pass": "test2026"},
            {"id": 103, "phone": "09833333333", "name": "Tester Three", "pass": "user1010"},
            {"id": 104, "phone": "09844444444", "name": "Tester Four", "pass": "seed5555"},
            {"id": 105, "phone": "09855555555", "name": "Tester Five", "pass": "demo9999"},
        ]

        for tester in tester_accounts:
            self.stdout.write(f'Seeding Tester Account: {tester["name"]} ({tester["phone"]}) ID: {tester["id"]}')
            
            # Check if username or ID already exists to avoid conflict
            User.objects.filter(id=tester["id"]).delete()
            User.objects.filter(username=tester["phone"]).delete()
            
            user = User.objects.create(
                id=tester["id"],
                username=tester["phone"]
            )
            user.set_password(tester["pass"])
            user.save()

            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.full_name = tester["name"]
            profile.phone_number = tester["phone"]
            profile.save()

            # 3. Write mock local CSV datasets
            self.generate_local_files(tester["id"])
            self.stdout.write(f'  Created local datasets at api/local_datasets/user_{tester["id"]}/')

        self.stdout.write(self.style.SUCCESS('Successfully seeded sample database data and 5 tester mock local datasets.'))
