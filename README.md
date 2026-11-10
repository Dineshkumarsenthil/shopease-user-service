# ShopEase User Management Service

Independent FastAPI microservice that manages customer profiles and delivery addresses.
It has its own MySQL 8 database (`shopease_user_db`) and its own Docker containers.
It does **not** implement login or registration: those stay in the Authentication Service
(`shopease-auth-service`). Every request carries the JWT issued by that service.

## Technology stack
Python 3.11, FastAPI, SQLAlchemy, Alembic, MySQL 8, PyJWT, Pydantic, Docker, Docker Compose.

## Folder structure
```
shopease-user-service/
├── app/
│   ├── main.py                       # creates app, registers routers, health check
│   ├── routers/user_routes.py        # profile + account endpoints (HTTP only)
│   ├── routers/address_routes.py     # address endpoints (HTTP only)
│   ├── services/user_service.py      # profile logic + "current profile" dependencies
│   ├── services/address_service.py   # address logic, ownership checks, default-address rule
│   ├── models/user_model.py          # user_profiles table
│   ├── models/address_model.py       # user_addresses table
│   ├── schemas/user_schema.py        # Pydantic validation for profiles
│   ├── schemas/address_schema.py     # Pydantic validation for addresses
│   ├── core/config.py                # settings from environment variables
│   ├── core/security.py              # JWT validation -> authenticated user id
│   └── database/connection.py        # engine, session, get_db, safe_commit (rollback)
├── alembic/  alembic.ini             # migrations (versions/0001_create_user_tables.py)
├── tests/test_user_service.py        # automated tests (25)
├── postman/                          # Postman collection
├── Dockerfile  docker-compose.yml  requirements.txt
├── .env.example  .dockerignore  .gitignore
└── README.md
```

## Database (`shopease_user_db`)
**user_profiles**: id, auth_user_id (UNIQUE), full_name, phone_number, date_of_birth, gender,
profile_image, is_active, created_at, updated_at.
**user_addresses**: id, user_id (FK -> user_profiles.id, ON DELETE CASCADE), address_type, full_name,
phone_number, address_line_1, address_line_2, city, state, country, postal_code, is_default, created_at.

`is_active` is the only column added to the specification. It stores the profile status used by account
deactivation (see below). No passwords or credentials are stored in this service.

## Environment variables
```
copy .env.example .env      # Windows   (cp on Linux/Mac)
```
| Variable | Meaning |
|---|---|
| MYSQL_ROOT_PASSWORD, MYSQL_DATABASE, MYSQL_USER, MYSQL_PASSWORD | Database container and connection settings |
| JWT_SECRET_KEY, JWT_ALGORITHM | **Must be identical to the values in shopease-auth-service/.env** |
| AUTH_SERVICE_URL | Location of the Authentication Service (default `http://host.docker.internal:8001`) |

Never commit `.env`.

## Authentication integration
1. The user registers and logs in at the Authentication Service (`POST /api/auth/register`, `/api/auth/login`) and gets a JWT.
2. The client sends it here as `Authorization: Bearer <token>`.
3. `app/core/security.py` verifies the signature and expiry with the shared secret and reads the user id from the `sub` claim.
   Missing, invalid or expired tokens return **401**.
4. The profile is always found with that id (`auth_user_id`). No endpoint accepts a user id from the request body
   (unknown body fields such as `auth_user_id` are rejected with 422), so users can only reach their own data.
5. Not allowed -> **403**: an address that belongs to another user, or any profile/address call on a deactivated profile.
   Address id that does not exist -> **404**.

## Account status: how both services behave
| Action | User Service | Authentication Service |
|---|---|---|
| `PATCH /api/users/profile/deactivate` | Profile `is_active=false`. Profile and address APIs return 403. `GET /api/users/account` still works and shows the status. | **Nothing changes.** The account is not deleted or disabled and the user can still log in. |
| `PATCH /api/users/profile/reactivate` | Profile active again. | Nothing changes. |
| `DELETE /api/users/profile` | Profile and its addresses are deleted. | Nothing changes. |
| Account disabled in the Auth Service | Login stops there, so no new tokens are issued. Tokens already issued stay valid until they expire (this service validates the token locally). | Owner of the account status. |

The Authentication Service stays the single owner of login credentials and account status.

## API endpoints (all need a Bearer token)
| Method | Endpoint | Purpose | Codes |
|---|---|---|---|
| POST | /api/users/profile | Create profile | 201, 409 duplicate, 422 |
| GET | /api/users/profile | Get own profile | 200, 404, 403 |
| PUT | /api/users/profile | Replace profile data | 200, 422 |
| PATCH | /api/users/profile | Partial update | 200, 422 |
| DELETE | /api/users/profile | Delete own profile and addresses | 200 |
| PATCH | /api/users/profile/deactivate | Deactivate profile | 200, 409 |
| PATCH | /api/users/profile/reactivate | Reactivate profile | 200, 409 |
| GET | /api/users/account | Profile + all addresses | 200 |
| POST | /api/users/addresses | Add address (first one is default) | 201, 422 |
| GET | /api/users/addresses | List own addresses (default first) | 200 |
| GET | /api/users/addresses/{id} | One address | 200, 403, 404 |
| PUT | /api/users/addresses/{id} | Update address | 200, 403, 404, 422 |
| DELETE | /api/users/addresses/{id} | Delete address | 200, 403, 404 |
| PATCH | /api/users/addresses/{id}/default | Set default address | 200, 403, 404 |

Rules: phone numbers have 10 to 15 digits (optional +); date of birth cannot be in the future; gender is
Male/Female/Other; address type is Home/Office/Other; only one default address per user (setting a new default
clears the old one; deleting the default promotes the oldest remaining address).

## Alembic migrations
Run automatically when the container starts (`alembic upgrade head`). Manual commands:
```
docker compose exec user-service alembic upgrade head
docker compose exec user-service alembic current
docker compose exec user-service alembic downgrade -1
```

## Docker setup and run
Start the Authentication Service first (host port 8001), then:
```
docker compose up -d --build
docker compose ps
docker compose logs user-service
```
Swagger UI: http://localhost:8002/docs. MySQL is published on host port 3308.
Stop: `docker compose down` (add `-v` to delete the database volume).

## API testing
- Automated: `pip install -r requirements.txt` then `pytest -q` (SQLite in memory) -> 25 tests pass.
- Manual: Swagger UI and Postman. Import `postman/ShopEase_User_Service.postman_collection.json`
  (requests S1 to S4 register and log in two users on the Auth Service and save `token_a` / `token_b`).

| # | Scenario | Expected | Automated test |
|---|---|---|---|
| 1 | Profile API without token | 401 | Pass |
| 2 | Profile API with invalid token | 401 | Pass |
| 3 | Create profile with valid token | 201 | Pass |
| 4 | Create duplicate profile | 409 | Pass |
| 5 | Get own profile | 200 | Pass |
| 6 | Update profile (PUT) | 200 | Pass |
| 7 | Partial update (PATCH) | 200 | Pass |
| 8 | Add multiple addresses | 201 | Pass |
| 9 | List addresses | 200 | Pass |
| 10 | Update address | 200 | Pass |
| 11 | Set default address | 200 | Pass |
| 12 | Only one default address exists | 1 default | Pass |
| 13 | Delete address | 200, then 404 | Pass |
| 14 | Another user's profile | own data only (404 if none) | Pass |
| 15 | Another user's address | 403 | Pass |
| 16 | Database records after each operation | verified in MySQL | See screenshots |
