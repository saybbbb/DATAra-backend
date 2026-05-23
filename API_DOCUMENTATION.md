# API Documentation & HTTPie Testing Results

## 1. Register User Endpoint (POST `/api/register/`)
**Command:**
```bash
http --ignore-stdin POST 127.0.0.1:8000/api/register/ username=09998887776 phone_number=09998887776 password=testpassword123
```
**Response:**
```json
{
  "message": "User registered successfully",
  "token": "b14c61539118540321c5d3187c99cae29e0429bf"
}
```

## 2. Login User Endpoint (POST `/api/login/`)
**Command:**
```bash
http --ignore-stdin POST 127.0.0.1:8000/api/login/ username=09998887776 password=testpassword123
```
**Response:**
```json
{
  "message": "Login successful",
  "user_id": 7,
  "username": "09998887776",
  "token": "b14c61539118540321c5d3187c99cae29e0429bf"
}
```

## 3. Get User Profile (GET `/api/profile/`)
**Command:**
```bash
http --ignore-stdin GET 127.0.0.1:8000/api/profile/ "Authorization: Token b14c61539118540321c5d3187c99cae29e0429bf"
```
**Response:**
```json
{
  "username": "09998887776",
  "email": "",
  "phone_number": "09998887776",
  "address": "",
  "provider": "DESU"
}
```

## 4. Update User Profile (PUT `/api/profile/`)
**Command:**
```bash
http --ignore-stdin PUT 127.0.0.1:8000/api/profile/ username=UpdatedUser address="Manila, Philippines" "Authorization: Token b14c61539118540321c5d3187c99cae29e0429bf"
```
**Response:**
```json
{
  "username": "UpdatedUser",
  "email": "",
  "phone_number": "09998887776",
  "address": "Manila, Philippines",
  "provider": "DESU"
}
```

## 5. Add Data Usage Record (POST `/api/usage/`)
**Command:**
```bash
http --ignore-stdin POST 127.0.0.1:8000/api/usage/ app_name="Facebook" data_used_mb=250.5 date="2026-05-01" time_slot="10:00:00" "Authorization: Token b14c61539118540321c5d3187c99cae29e0429bf"
```
**Response:**
```json
{
  "id": 2,
  "date": "2026-05-01",
  "time_slot": "10:00:00",
  "data_used_mb": 250.5,
  "app_name": "Facebook",
  "created_at": "2026-05-01T08:39:38.664743Z"
}
```

## 6. Get Usage Summary (GET `/api/usage/summary/`)
**Command:**
```bash
http --ignore-stdin GET 127.0.0.1:8000/api/usage/summary/ "Authorization: Token b14c61539118540321c5d3187c99cae29e0429bf"
```
**Response:**
```json
{
  "total_used_mb": 501.0,
  "total_limit_mb": 14336,
  "daily_average_mb": 501.0,
  "top_app": "Facebook",
  "top_app_usage_mb": 501.0
}
```
