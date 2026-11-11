# ShopEase User Management Service

A FastAPI microservice that manages customer profiles and delivery addresses. It has its own MySQL 8 database (`shopease_user_db`) and runs in Docker. Login and registration stay in the Authentication Service (`shopease-auth-service`), and every request here uses the JWT issued by that service.

**Stack:** Python 3.11, FastAPI, SQLAlchemy, Alembic, MySQL 8, PyJWT, Docker Compose.

## Folder structure

```
shopease-user-service/
├── app/
│   ├── main.py            # app startup and router registration
│   ├── routers/           # profile and address endpoints
│   ├── services/          # business logic
│   ├── models/            # user_profiles and user_addresses tables
│   ├── schemas/           # Pydantic validation
│   ├── core/              # config and JWT validation
│   └── database/          # connection and session
├── alembic/               # migrations
├── tests/                 # automated tests
├── postman/               # Postman collection
├── docs/                  # test report and screenshots
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Setup

Start the Authentication Service first (port 8001), then run:

```
copy .env.example .env
docker compose up -d --build
```

Use `cp` instead of `copy` on Linux or Mac. The Alembic migration runs automatically when the container starts.

- Swagger UI: http://localhost:8002/docs
- MySQL: `127.0.0.1`, port `3308`

Stop with `docker compose down`.

## Environment variables

| Variable | Meaning |
|---|---|
| MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD | Database settings |
| JWT_SECRET_KEY, JWT_ALGORITHM | Must match the Authentication Service's `.env` |
| AUTH_SERVICE_URL | Authentication Service address |

Never commit `.env`.

## How authentication works

Log in at the Authentication Service to get a token, then send it here as `Authorization: Bearer <token>`. The service checks the token and reads the user id from it, so users can only reach their own data. A missing or invalid token returns 401, someone else's address returns 403, and a missing record returns 404.

## API endpoints

All endpoints need a Bearer token.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | /api/users/profile | Create profile (201, 409 if it exists) |
| GET | /api/users/profile | Get own profile |
| PUT | /api/users/profile | Update profile |
| PATCH | /api/users/profile | Partial update |
| DELETE | /api/users/profile | Delete profile and addresses |
| PATCH | /api/users/profile/deactivate | Deactivate profile |
| PATCH | /api/users/profile/reactivate | Reactivate profile |
| GET | /api/users/account | Profile with all addresses |
| POST | /api/users/addresses | Add address |
| GET | /api/users/addresses | List addresses |
| GET | /api/users/addresses/{id} | Get one address |
| PUT | /api/users/addresses/{id} | Update address |
| DELETE | /api/users/addresses/{id} | Delete address |
| PATCH | /api/users/addresses/{id}/default | Set default address |

Each user has only one default address. Deactivating a profile does not change the Authentication Service, and the user can still log in there.

## Database

`user_profiles` has a unique `auth_user_id`. `user_addresses` links to it with `user_id` (cascade delete). The only extra column beyond the specification is `is_active` on profiles.

## Testing

Automated tests: `pip install -r requirements.txt` then `pytest -q`.

Manual tests: use Swagger UI, or import `postman/ShopEase_User_Service.postman_collection.json` into Postman or Bruno. The test report with screenshots is in `docs/`.

## Author

Dineshkumar S
