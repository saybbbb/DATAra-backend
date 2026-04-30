# DATAra Backend

Backend API for **DATAra** — a mobile data usage monitoring and prediction system.

## Tech Stack
- Python 3.x
- Django 5.x
- Django REST Framework

## Features
- User authentication (register/login)
- Data usage tracking and recording
- Usage history retrieval
- User profile management

## Setup
1. Create virtual environment: `python -m venv venv`
2. Activate: `venv\Scripts\activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Start server: `python manage.py runserver`

## Map System Features to Django MVT Architecture
| UI Feature (Mobile) | Model (M)        | View (V)                        | Template (T)   |
|:-------------------|:-----------------|:--------------------------------|:---------------|
| Login / Register   | User             | LoginView, RegisterView         | N/A (JSON API) |
| Dashboard          | DataUsageRecord  | DashboardView                   | N/A (JSON API) |
| History            | DataUsageRecord  | UsageHistoryView                | N/A (JSON API) |
| Profile            | UserProfile      | ProfileView                     | N/A (JSON API) |
| Settings           | User             | Profile/Auth handled            | N/A (JSON API) |
> [!NOTE]
> Since this is a REST API backend, there are **no Django templates**. The "Template" layer is replaced by the React Native mobile frontend that consumes JSON responses.

## Project Structure
```text
DATAra-backend/
├── api/
│   ├── __init__.py
│   ├── admin.py          # Admin registrations for UserProfile & DataUsageRecord
│   ├── apps.py
│   ├── models.py         # DataUsageRecord + UserProfile models
│   ├── serializers.py    # All serializers
│   ├── urls.py           # API URL routing
│   └── views.py          # API views (root, register, login, usage, profile)
├── datara_backend/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py       # With DRF config + app registrations
│   ├── urls.py           # Main URL config (includes api.urls)
│   └── wsgi.py
├── .gitignore
├── manage.py
├── README.md
└── requirements.txt
```

## API Endpoint Summary
| Method | Endpoint              | Auth Required | Description                          |
|--------|----------------------|---------------|--------------------------------------|
| GET    | `/api/`                | No            | API root with endpoint listing       |
| POST   | `/api/register/`       | No            | Register a new user                  |
| POST   | `/api/login/`          | No            | Log in with credentials              |
| GET    | `/api/usage/`          | Yes           | List user's data usage records       |
| POST   | `/api/usage/`          | Yes           | Create a new usage record            |
| GET    | `/api/usage/summary/`  | Yes           | Dashboard summary (totals, averages) |
| GET    | `/api/profile/`        | Yes           | Get user profile                     |
| PUT    | `/api/profile/`        | Yes           | Update user profile                  |

## Mobile ↔ Backend Mapping
| Mobile Screen          | API Endpoint(s) Used              |
|-----------------------|----------------------------------|
| Login (`index.tsx`)     | POST `/api/login/`                 |
| Register (`register.tsx`)| POST `/api/register/`            |
| Dashboard (`dashboard.tsx`) | GET `/api/usage/summary/`     |
| History (`history.tsx`) | GET `/api/usage/`                 |
| Profile (`profile.tsx`) | GET `/api/profile/`, PUT `/api/profile/` |
