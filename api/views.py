from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from .models import UserProfile, DataUsageRecord
from .serializers import RegisterSerializer, LoginSerializer, DataUsageRecordSerializer, UserProfileSerializer


@api_view(['GET'])
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
        serializer.save()
        return Response(
            {"message": "User registered successfully"},
            status=status.HTTP_201_CREATED
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        user = authenticate(
            username=serializer.validated_data['username'],
            password=serializer.validated_data['password']
        )
        if user:
            return Response({
                "message": "Login successful",
                "user_id": user.id,
                "username": user.username,
            })
        return Response(
            {"error": "Invalid credentials"},
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
        "total_used_mb": round(total_used, 2),
        "total_limit_mb": 14336,         # 14 GB in MB — adjust as needed
        "daily_average_mb": round(daily_avg, 2),
        "top_app": top_app_qs['app_name'] if top_app_qs else None,
        "top_app_usage_mb": round(top_app_qs['total'], 2) if top_app_qs else 0,
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def profile_view(request):
    """
    GET — Retrieve the user's profile
    PUT — Update the user's profile
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
