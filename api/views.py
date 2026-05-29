import os
import json
from pathlib import Path
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from .models import UserProfile, DataUsageRecord
from .serializers import RegisterSerializer, LoginSerializer, DataUsageRecordSerializer, UserProfileSerializer
from rest_framework.authtoken.models import Token

@api_view(['GET'])
@permission_classes([AllowAny])
def api_root(request):
    return Response({
        "message": "Welcome to DATAra API",
        "endpoints": {
            "register": "/api/register/",
            "login": "/api/login/",
            "usage": "/api/usage/",
            "profile": "/api/profile/",
        }
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, created = Token.objects.get_or_create(user=user)
        return Response(
            {"message": "User registered successfully", "token": token.key},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        from django.contrib.auth.models import User
        try:
            user_obj = User.objects.get(username=username)
        except User.DoesNotExist:
            from .models import UserProfile
            if UserProfile.objects.filter(phone_number__endswith=f"_{username}").exists():
                return Response({"error": "This account was deleted."}, status=status.HTTP_404_NOT_FOUND)
            return Response({"error": "Account does not exist."}, status=status.HTTP_404_NOT_FOUND)
            
        if not user_obj.is_active:
            return Response({"error": "Account is inactive or has been deleted."}, status=status.HTTP_403_FORBIDDEN)
            
        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username,
                "token": token.key,
            })
        return Response(
            {"error": "Invalid password."},
            status=status.HTTP_401_UNAUTHORIZED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def usage_list(request):
    """
    GET  — List all usage records for the logged-in user
    POST — Create a new usage record
    """
    if request.method == 'GET':
        records = DataUsageRecord.objects.filter(user=request.user)
        serializer = DataUsageRecordSerializer(records, many=True)
        return Response(serializer.data)
    elif request.method == 'POST':
        serializer = DataUsageRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def usage_detail(request, pk):
    """
    DELETE — Remove a specific usage record
    """
    try:
        record = DataUsageRecord.objects.get(pk=pk, user=request.user)
        record.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    except DataUsageRecord.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_summary(request):
    """
    Returns dashboard summary data:
    - total_used_mb
    - total_limit_mb (hardcoded for now, or from user profile)
    - daily_average_mb
    - top_app
    """
    records = DataUsageRecord.objects.filter(user=request.user)
    total_used = sum(r.data_used_mb for r in records)
    unique_dates = records.values('date').distinct().count()
    daily_avg = total_used / unique_dates if unique_dates > 0 else 0
    # Top app by usage
    from django.db.models import Sum
    top_app_qs = (
        records.values('app_name')
        .annotate(total=Sum('data_used_mb'))
        .order_by('-total')
        .first()
    )
    return Response({
        "full_name": request.user.profile.full_name if hasattr(request.user, 'profile') else request.user.username,
        "total_used_mb": round(total_used, 2),
        "total_limit_mb": 14336,         # 14 GB in MB — adjust as needed
        "daily_average_mb": round(daily_avg, 2),
        "top_app": top_app_qs['app_name'] if top_app_qs else None,
        "top_app_usage_mb": round(top_app_qs['total'], 2) if top_app_qs else 0,
    })


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    GET — Retrieve the user's profile
    PUT — Update the user's profile
    DELETE — Soft delete the user account
    """
    try:
        profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return Response(
            {"error": "Profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )
    if request.method == 'GET':
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)
    elif request.method == 'PUT':
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    elif request.method == 'DELETE':
        import uuid
        user = request.user
        
        # Free up the username so the user can register again with the same number
        user.username = f"del_{user.id}_{uuid.uuid4().hex[:8]}"
        user.is_active = False
        user.save()
        
        # Also free up the phone number in profile
        profile.phone_number = f"del_{profile.phone_number}"
        profile.save()
        
        return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def ml_metrics_view(request):
    """
    GET — Dynamically calculate and fetch ML model performance metrics
    """
    base_dir = Path(settings.BASE_DIR)
    model_path = base_dir / 'api' / 'ml_models' / 'data_depletion_model.joblib'
    
    if not model_path.exists():
        return Response(
            {"error": "ML model not found. Please ensure the model is trained."},
            status=status.HTTP_404_NOT_FOUND
        )
        
    try:
        import joblib
        import pandas as pd
        import numpy as np
        import glob
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        
        # Load the model
        model_data = joblib.load(model_path)
        model = model_data.get('model')
        features = model_data.get('features', [])
        aggregated_hourly_mean = model_data.get('aggregated_hourly_mean', 15.0)
        
        if model is None:
            return Response(
                {"error": "Trained model object is null inside joblib container."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        # Search for data harvest CSV files to compute evaluation dynamically
        csv_dir = base_dir.parent / 'CSV'
        csv_files = glob.glob(str(csv_dir / "data_harvest*.csv"))
        
        if not csv_files:
            return Response(
                {"error": "No dataset CSV files found to compute evaluation metrics."},
                status=status.HTTP_404_NOT_FOUND
            )
            
        dfs = []
        for f in csv_files:
            try:
                dfs.append(pd.read_csv(f))
            except Exception:
                continue
                
        if not dfs:
            return Response(
                {"error": "Failed to read any dataset CSV files."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        df = pd.concat(dfs, ignore_index=True)
        
        # Preprocessing matching the training logic
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['hour'] = df['datetime'].dt.hour
        
        if 'network_type' in df.columns:
            cellular_df = df[df['network_type'].isin(['CELLULAR', 'MOBILE'])]
            if len(cellular_df) > 100:
                df = cellular_df
                
        df['date'] = df['datetime'].dt.date
        
        agg_dict = {'mb_used': 'sum'}
        if 'screen_on' in df.columns:
            agg_dict['screen_on'] = 'mean'
        if 'battery_level' in df.columns:
            agg_dict['battery_level'] = 'mean'
            
        hourly_df = df.groupby(['date', 'hour', 'day_of_week', 'is_weekend']).agg(agg_dict).reset_index()
        
        # Prepare feature vectors
        if 'screen_on' in hourly_df.columns:
            hourly_df['screen_on'] = hourly_df['screen_on'].fillna(0.0)
        if 'battery_level' in hourly_df.columns:
            hourly_df['battery_level'] = hourly_df['battery_level'].fillna(50.0)
            
        X = hourly_df[features]
        y = hourly_df['mb_used']
        
        # Predict on dataset
        y_pred = model.predict(X)
        
        # Calculate dynamic metrics
        mae = mean_absolute_error(y, y_pred)
        mse = mean_squared_error(y, y_pred)
        rmse = np.sqrt(mse)
        r2 = r2_score(y, y_pred)
        
        # Determine model type dynamically based on the model object class name
        model_name = model.__class__.__name__
        if model_name == 'RandomForestRegressor':
            model_type = "Random Forest"
        elif model_name == 'XGBRegressor':
            model_type = "XGBoost"
        elif model_name == 'LinearRegression':
            model_type = "Linear Regression"
        else:
            import re
            model_type = re.sub(r'(?<!^)(?=[A-Z])', ' ', model_name.replace('Regressor', '').replace('Regression', ''))

        metrics_data = {
            "model_type": model_type,
            "mae_mb": float(mae),
            "rmse_mb": float(rmse),
            "r2_score": float(r2),
            "features_used": features,
            "dataset_size_records": int(len(hourly_df))
        }
        return Response(metrics_data)
        
    except Exception as e:
        return Response(
            {"error": f"Failed to compute dynamic metrics: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )