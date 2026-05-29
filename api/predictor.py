import os
import joblib
import datetime
from pathlib import Path

# Load the trained model and feature list
BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_PATH_ENV = os.environ.get('ML_MODEL_PATH')
MODEL_PATH = Path(MODEL_PATH_ENV) if MODEL_PATH_ENV else BASE_DIR / 'api' / 'ml_models' / 'data_depletion_model.joblib'

class DataUsagePredictor:
    def __init__(self):
        self.model = None
        self.features = []
        self.fallback_hourly_mb = 15.0 # fallback: ~15MB/hour
        self.load_model()
        
    def load_model(self):
        try:
            if MODEL_PATH.exists():
                data = joblib.load(MODEL_PATH)
                self.model = data.get('model')
                self.features = data.get('features', [])
                self.fallback_hourly_mb = data.get('aggregated_hourly_mean', 15.0)
                print(f"Loaded trained Random Forest model from {MODEL_PATH}. Fallback mean: {self.fallback_hourly_mb:.2f} MB/hr")
            else:
                print(f"Trained model not found at {MODEL_PATH}. Running in fallback rule-based mode.")
        except Exception as e:
            print(f"Error loading model: {e}. Running in fallback rule-based mode.")
            self.model = None

    def predict_hourly(self, hour, day_of_week, is_weekend, screen_on=0.5, battery_level=80.0):
        """Predicts data usage in MB for a single hour."""
        if self.model is not None:
            try:
                # Prepare features DataFrame/array matching training
                import pandas as pd
                input_data = {
                    'hour': [hour],
                    'day_of_week': [day_of_week],
                    'is_weekend': [is_weekend]
                }
                if 'screen_on' in self.features:
                    input_data['screen_on'] = [screen_on]
                if 'battery_level' in self.features:
                    input_data['battery_level'] = [battery_level]
                    
                df = pd.DataFrame(input_data)
                pred = self.model.predict(df)[0]
                return max(0.0, float(pred)) # no negative usage
            except Exception as e:
                # Silent fallback in case of feature shape mismatch
                return self.fallback_hourly_mb
        else:
            # Fallback simple profile based on hour of the day
            # Night usage is lower, daytime usage is higher
            if 0 <= hour <= 6:
                return self.fallback_hourly_mb * 0.2 # 3MB
            elif 18 <= hour <= 23:
                return self.fallback_hourly_mb * 1.5 # 22.5MB (peak hours)
            else:
                return self.fallback_hourly_mb # 15MB

    def project_depletion(self, remaining_mb, expiry_time_str, screen_on=0.5, battery_level=80.0):
        """
        Projects forward hour-by-hour to estimate when data will run out.
        
        Parameters:
        - remaining_mb: current remaining data limit in MB
        - expiry_time_str: expiry time in ISO format (YYYY-MM-DDTHH:MM:SS)
        """
        now = datetime.datetime.now()
        
        try:
            expiry = datetime.datetime.fromisoformat(expiry_time_str.replace('Z', ''))
        except Exception:
            # If parsing fails, default to 48 hours from now
            expiry = now + datetime.timedelta(hours=48)
            
        time_left = expiry - now
        hours_to_expiry = max(1.0, time_left.total_seconds() / 3600.0)
        
        current_mb = 0.0
        projected_hours = 0
        predictions_history = []
        
        # Simulate hour by hour up to a max of 720 hours (30 days)
        sim_time = now
        runs_out = False
        depletion_time = None
        
        while current_mb < remaining_mb and projected_hours < 720:
            sim_time = sim_time + datetime.timedelta(hours=1)
            projected_hours += 1
            
            # Extract features for this simulated hour
            hour = sim_time.hour
            day_of_week = sim_time.isoweekday() # 1=Mon, 7=Sun
            is_weekend = 1 if day_of_week >= 6 else 0
            
            # Predict hourly usage
            pred_mb = self.predict_hourly(hour, day_of_week, is_weekend, screen_on, battery_level)
            current_mb += pred_mb
            predictions_history.append({
                "hour_offset": projected_hours,
                "predicted_mb": round(pred_mb, 2),
                "cumulative_mb": round(current_mb, 2)
            })
            
            if current_mb >= remaining_mb:
                runs_out = True
                depletion_time = sim_time
                break
                
        # Calculate results
        if runs_out:
            hours_remaining = projected_hours
            depletion_timestamp = depletion_time.isoformat()
            # If it runs out before expiry, we warn the user
            runs_out_before_expiry = hours_remaining < hours_to_expiry
        else:
            # Doesn't run out within projection window or before expiry
            hours_remaining = 720
            depletion_timestamp = (now + datetime.timedelta(hours=720)).isoformat()
            runs_out_before_expiry = False
            
        # Determine usage pace:
        # If it runs out in less than 50% of the expiry time -> Extreme
        # If it runs out in less than 100% of the expiry time -> Warning
        # Else -> Normal
        if runs_out_before_expiry:
            ratio = hours_remaining / hours_to_expiry
            if ratio < 0.5:
                usage_pace = "extreme"
            elif ratio < 0.75:
                usage_pace = "warning"
            else:
                usage_pace = "moderate"
        else:
            usage_pace = "normal"
            
        return {
            "hours_remaining": round(hours_remaining, 1),
            "depletion_time": depletion_timestamp,
            "runs_out_before_expiry": runs_out_before_expiry,
            "usage_pace": usage_pace,
            "hours_to_expiry": round(hours_to_expiry, 1),
            "predicted_trajectory": predictions_history[:24] # next 24 hours of predictions
        }
