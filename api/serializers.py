from rest_framework import serializers
from django.contrib.auth.models import User
from .models import DataUsageRecord, UserProfile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    phone_number = serializers.CharField(max_length=15)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'phone_number']

    def create(self, validated_data):
        phone_number = validated_data.pop('phone_number')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        UserProfile.objects.create(user=user, phone_number=phone_number)
        return user


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username')
    email = serializers.CharField(source='user.email', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['username', 'email', 'phone_number', 'address', 'provider']

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', None)
        if user_data and 'username' in user_data:
            instance.user.username = user_data['username']
            instance.user.save()
        return super().update(instance, validated_data)


class DataUsageRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataUsageRecord
        fields = ['id', 'date', 'time_slot', 'data_used_mb', 'app_name', 'created_at']
        read_only_fields = ['id', 'created_at']
