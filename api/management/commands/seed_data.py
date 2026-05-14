from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from api.models import DataUsageRecord
from datetime import date, timedelta
import random

class Command(BaseCommand):
    help = 'Seeds the database with sample data usage records'

    def handle(self, *args, **kwargs):
        # Define our 3 test accounts based on 14GB (14336MB) monthly limit
        # Target for 28 days:
        # Normal: ~6GB (42%) -> ~214MB/day -> ~40-45MB/slot (5 slots)
        # Warning: ~11.5GB (80%) -> ~410MB/day -> ~75-85MB/slot (5 slots)
        # Extreme: ~13.5GB (94%) -> ~482MB/day -> ~90-105MB/slot (5 slots)
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

        # Ensure these users exist
        from api.models import UserProfile
        users_to_seed = []
        for acc in test_accounts:
            user, created = User.objects.get_or_create(username=acc["phone"])
            if created:
                user.set_password("password123")
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
            self.stdout.write(f'Seeding data for {acc["name"]} ({acc["phone"]}) - {acc["tier"]} tier')
            
            # Generate data for the last 28 days
            for i in range(28):
                current_date = date.today() - timedelta(days=i)
                # Generate exactly 5 slots per day to hit targets reliably
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
                    
        self.stdout.write(self.style.SUCCESS('Successfully seeded data usage records.'))
