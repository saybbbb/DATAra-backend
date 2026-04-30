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