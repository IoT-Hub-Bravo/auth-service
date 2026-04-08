# auth-service

The **Identity Provider (IdP)** for the IoT Hub microservices platform.

This service is the single source of truth for user identity. It authenticates
credentials, issues cryptographically signed JWT access tokens (RS256), and
publishes its public key via a standard JWKS endpoint so that every other
microservice can validate tokens **locally** — without querying this service or
the database on each request.

---

## Table of Contents

- [Overview & Architecture](#overview--architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Local Setup](#local-setup)
  - [Prerequisites](#prerequisites)
  - [RSA Key Generation](#rsa-key-generation)
  - [Environment Configuration](#environment-configuration)
  - [Running in the Dev Workspace](#running-in-the-dev-workspace)
  - [Dev User Seeding](#dev-user-seeding)
- [API Reference](#api-reference)
  - [POST /api/auth/login/](#post-apiauthloin)
  - [GET /api/auth/.well-known/jwks.json](#get-apiauthwell-knownjwksjson)
  - [GET /api/health/](#get-apihealth)
- [Integration Guide](#integration-guide)
- [Running Tests](#running-tests)
- [User Model & Roles](#user-model--roles)
- [Configuration Reference](#configuration-reference)

---

## Overview & Architecture

### Responsibility

`auth-service` has exactly one domain: **user authentication**. It does not
manage devices, telemetry, or any other business entity. This strict boundary
keeps it small, auditable, and independently deployable.

### How it fits into the platform

```
                        ┌─────────────────────────────────────────┐
                        │           iot-hub-nw (Docker network)   │
                        │                                         │
  Client                │  ┌──────────────────┐                  │
    │                   │  │  gateway (Nginx)  │                  │
    │ POST /api/auth/   │  │                  │                  │
    │─────────────────────▶│  /api/auth/*  ──▶│──▶  auth-service │
    │                   │  │  /api/*       ──▶│──▶  device-reg.. │
    │◀────────────────────▶│                  │                  │
    │  { access_token } │  └──────────────────┘                  │
    │                   │                                         │
    │ GET /api/devices/ │                          ┌──────────────┤
    │ Authorization:    │                          │  auth-service│
    │ Bearer <token>    │                          │  :8001       │
    │─────────────────────────────────────────────▶│              │
    │                   │                          │  Signs JWTs  │
    │                   │   device-registry        │  with RSA    │
    │                   │   validates token        │  private key │
    │                   │   locally using          │              │
    │                   │   cached public key      │  Exposes     │
    │                   │   ← NO call to           │  JWKS public │
    │                   │     auth-service         │  key endpoint│
    │◀─────────────────────────────────────────────┘              │
    │  200 OK           │                                         │
                        └─────────────────────────────────────────┘
```

### Decentralized validation — the key design decision

After issuing a token, `auth-service` is **not involved** in subsequent API
calls. Each consuming microservice (e.g., `device-registry`) fetches
`auth-service`'s RSA public key once via the JWKS endpoint, caches it locally,
and uses it to cryptographically verify every incoming token on its own. This
means:

- **No synchronous inter-service calls on the hot path** — latency stays low
  regardless of `auth-service` availability
- **`auth-service` can be restarted or scaled independently** without affecting
  in-flight requests to other services
- **A compromised consumer cannot forge tokens** — it holds only the public key,
  which is mathematically useless for signing

---

## Tech Stack

| Component | Technology |
|---|---|
| Web framework | Django 5.2 |
| WSGI server | Gunicorn |
| Database | PostgreSQL 16 |
| JWT signing | PyJWT 2.9 (RS256) |
| Cryptography | `cryptography` 42 |
| Static files | WhiteNoise |
| Containerisation | Docker, Docker Compose |
| Shared library | `iot-hub-shared` (custom internal package) |
| Test framework | pytest + pytest-django |

---

## Project Structure

```
auth-service/
├── compose/
│   ├── runtime.yml        # Used by the dev workspace (shared postgres, shared network)
│   └── standalone.yml     # Self-contained compose with its own postgres container
├── docker/
│   ├── Dockerfile
│   ├── entrypoint.sh      # Waits for pg_isready before starting
│   └── start.sh           # Runs migrate, optional setup_admin, then gunicorn
├── secrets/               # Git-ignored. Place PEM key files here.
│   └── .gitkeep
├── src/
│   ├── conftest.py        # Sets BUILD_TIME=1 before Django loads (for pytest)
│   ├── manage.py
│   ├── config/
│   │   ├── settings.py
│   │   └── urls.py
│   └── apps/
│       └── users/
│           ├── models/
│           │   └── user.py            # Custom User model with UserRole choices
│           ├── managers.py            # UserManager (create_user, create_superuser)
│           ├── services/
│           │   └── token_service.py   # RS256 token issuance via TokenService
│           ├── api/
│           │   ├── views.py           # login, jwks, healthcheck views
│           │   └── urls.py
│           └── management/
│               └── commands/
│                   └── setup_admin.py # Idempotent dev user seeding
├── .env.example
├── pytest.ini
└── requirements.txt
```

---

## Local Setup

### Prerequisites

- Docker and Docker Compose
- The `iot-hub-dev-workspace` repository checked out and its shared network
  created (`iot-hub-nw`)
- OpenSSL (for key generation)

### RSA Key Generation

`auth-service` requires an RSA 2048-bit key pair. Generate it once and place the
files in the `secrets/` directory (which is bind-mounted into the container at
`/run/secrets/`):

```bash
cd auth-service

# Generate the private key
openssl genrsa -out secrets/jwt_private.pem 2048

# Derive the public key from it
openssl rsa -in secrets/jwt_private.pem -pubout -out secrets/jwt_public.pem
```

> `secrets/*.pem` is listed in `.gitignore`. Never commit private key files.

### Environment Configuration

Copy the example file and fill in the required values:

```bash
cp .env.example .env
```

The most important variables for local development:

```ini
# ─── JWT ──────────────────────────────────────────────────────────────────────
JWT_PRIVATE_KEY_PATH=/run/secrets/jwt_private.pem
JWT_PUBLIC_KEY_PATH=/run/secrets/jwt_public.pem
JWT_ACCESS_TOKEN_TTL_SECONDS=3600
JWT_KEY_ID=auth-service-key-1

# ─── Django ───────────────────────────────────────────────────────────────────
# Generate with:
#   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
SECRET_KEY=your-generated-secret-key
DEBUG=true

# IMPORTANT: add "auth-service" so other containers on the iot-hub-nw network
# can reach this service by its container name
ALLOWED_HOSTS=localhost,127.0.0.1,auth-service

# ─── Database ─────────────────────────────────────────────────────────────────
DB_HOST=postgres      # shared postgres container in the dev workspace
DB_NAME=auth_db
DB_USER=auth_user
DB_PASSWORD=your-local-password

# ─── Dev user seeding ─────────────────────────────────────────────────────────
ALLOW_SETUP_ADMIN=true
DEV_SUPERUSER_PASSWORD=your-local-password
DEV_ADMIN_PASSWORD=your-local-password
DEV_CLIENT_PASSWORD=your-local-password
```

### Running in the Dev Workspace

Start `auth-service` alongside all shared infrastructure using the workspace
bootstrap script:

```bash
# From the iot-hub-dev-workspace root
./scripts/up.sh auth-service
```

This will:

1. Start the `infra` stack (Kafka) and the `shared` stack (Postgres, Redis) if
   not already running
2. Build the `auth-service` Docker image
3. Run database migrations automatically (`manage.py migrate`)
4. Seed development users if `ALLOW_SETUP_ADMIN=true`
5. Start Gunicorn on port `8001` inside the container

The service is then accessible:

| Route | URL |
|---|---|
| Via the API gateway (recommended) | `http://localhost/api/auth/` |
| Directly, bypassing the gateway | `http://localhost:8001/api/auth/` |

Verify the service is healthy:

```bash
curl http://localhost/api/health/
# {"status": "ok", "service": "auth-service"}
```

### Dev User Seeding

When `ALLOW_SETUP_ADMIN=true` is set, the container entrypoint automatically
runs `manage.py setup_admin` after migrations. This command is **idempotent** —
safe to leave enabled in local development; it skips any user that already
exists.

Three users are seeded by default:

| Username | Role | Password env var |
|---|---|---|
| `superadmin` | `admin` + Django superuser | `DEV_SUPERUSER_PASSWORD` |
| `admin_user` | `admin` | `DEV_ADMIN_PASSWORD` |
| `client_user` | `client` | `DEV_CLIENT_PASSWORD` |

Usernames and emails can be overridden with the corresponding `DEV_*_USERNAME`
and `DEV_*_EMAIL` environment variables.

> **Never set `ALLOW_SETUP_ADMIN=true` in a production environment.**

---

## API Reference

All endpoints are served under `/api/`. When accessed through the API gateway,
the base URL is `http://localhost/api/auth/`.

---

### POST /api/auth/login/

Authenticates a user and returns a signed RS256 JWT access token.

**Request**

```
POST /api/auth/login/
Content-Type: application/json
```

```json
{
  "username": "admin_user",
  "password": "your-password"
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `username` | `string` | Yes | The user's username |
| `password` | `string` | Yes | The user's password |

**Response — 200 OK**

```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6ImF1dGgtc2VydmljZS1rZXktMSIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIyIiwicm9sZSI6ImFkbWluIiwiaWF0IjoxNzQ0MDcwNDAwLCJleHAiOjE3NDQwNzQwMDAsImp0aSI6ImEzZjdjOTIxLTRiMmUtNGQxYS04ZjBlLTFjMmQzZTRmNWE2YiJ9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "token_type": "bearer",
  "expires_in": "2026-04-08T11:00:00Z"
}
```

| Field | Type | Description |
|---|---|---|
| `access_token` | `string` | RS256-signed JWT. Pass in subsequent requests as `Authorization: Bearer <token>` |
| `token_type` | `string` | Always `"bearer"` |
| `expires_in` | `string` | ISO 8601 UTC timestamp of when the token expires |

**JWT payload structure**

The token payload (readable at [jwt.io](https://jwt.io)) contains:

```json
{
  "sub":  "2",
  "role": "admin",
  "iat":  1744070400,
  "exp":  1744074000,
  "jti":  "a3f7c921-4b2e-4d1a-8f0e-1c2d3e4f5a6b"
}
```

| Claim | Description |
|---|---|
| `sub` | User's integer ID, serialised as a string (JWT standard) |
| `role` | User's role — `"admin"` or `"client"` |
| `iat` | Issued-at Unix timestamp |
| `exp` | Expiry Unix timestamp (`iat + JWT_ACCESS_TOKEN_TTL_SECONDS`) |
| `jti` | Unique token ID (UUID v4) — for audit trails and future revocation |

**Error responses**

| Status | Body | Cause |
|---|---|---|
| `400` | `{"error": "Invalid JSON body"}` | Malformed request body |
| `400` | `{"error": "Username is required"}` | Missing or non-string `username` |
| `400` | `{"error": "Password is required"}` | Missing or non-string `password` |
| `401` | `{"error": "Invalid credentials"}` | Wrong username or password |
| `405` | `{"error": "Method not allowed"}` | Non-POST request |

**curl example**

```bash
curl -X POST http://localhost/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin_user", "password": "your-password"}'
```

---

### GET /api/auth/.well-known/jwks.json

Returns the RSA public key in JSON Web Key Set (JWKS) format. Consuming
microservices fetch this endpoint once, cache the result locally, and use it to
validate tokens cryptographically without querying `auth-service` on every
request.

The response includes `Cache-Control: public, max-age=3600`.

**Request**

```
GET /api/auth/.well-known/jwks.json
```

No authentication required. No request body.

**Response — 200 OK**

```json
{
  "keys": [
    {
      "kty": "RSA",
      "use": "sig",
      "alg": "RS256",
      "kid": "auth-service-key-1",
      "n":   "0vx7agoebGcQSuuPiLJXZptN9nndrQmbXEps2aiAFbWhM78LhWx4cbbfAAtVT86zwu1RK7aPFFxuhDR1L6tSoc_BJECPebWKRXjBZCiFV4n3oknjhMstn64tZ_2W-5JsGY4Hc5n9yBXArwl93lqt7_RN5w6Cf0h4QyQ5v-65YGjQR0_FDW2QvzqY368QQMicAtaSqzs8KJZgnYb9c7d0zgdAZHzu6qMQvRL5hajrn1n91CbOpbISD08qNLyrdkt-bFTWhAI4vMQFh6WeZu0fM4lFd2NcRwr3XPksINHaQ-G_xBniIqbw0Ls1jF44-csFCur-kEgU8awapJzKnqDKgw",
      "e":   "AQAB"
    }
  ]
}
```

| Field | Description |
|---|---|
| `kty` | Key type — always `"RSA"` |
| `use` | Usage — `"sig"` (signature verification) |
| `alg` | Algorithm — `"RS256"` |
| `kid` | Key ID — matches the `kid` header embedded in every issued JWT |
| `n` | RSA modulus — Base64Url-encoded. Combined with `e`, this is the full public key. |
| `e` | RSA public exponent — almost always `AQAB` (65537) |

**curl example**

```bash
curl http://localhost/api/auth/.well-known/jwks.json
```

---

### GET /api/health/

Lightweight liveness probe used by the Docker Compose healthcheck and load
balancers.

**Response — 200 OK**

```json
{
  "status": "ok",
  "service": "auth-service"
}
```

---

## Integration Guide

To make any Django microservice a consumer of `auth-service`, follow these steps.
No changes to `auth-service` itself are required.

### Step 1 — Install `iot-hub-shared[auth_kit]`

Add to the service's `requirements.txt`:

```text
iot-hub-shared[auth_kit] @ git+https://github.com/IoT-Hub-Bravo/python-service-libs.git@v0.3.0
```

This installs `JWTAuthMiddleware`, `JWTValidator`, `login_required`,
`role_required`, and the `AuthenticatedUser` dataclass — along with their
dependencies (`PyJWT`, `cryptography`).

### Step 2 — Set `AUTH_KIT_JWKS_URI` in the service's `.env`

```ini
AUTH_KIT_JWKS_URI=http://auth-service:8001/api/auth/.well-known/jwks.json
AUTH_KIT_CACHE_TTL=3600
```

Both services must be on the same Docker network (`iot-hub-nw`) for the
container hostname `auth-service` to resolve correctly.

### Step 3 — Add `JWTAuthMiddleware` to `settings.py`

```python
# settings.py
from decouple import config

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # ... other middleware ...
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # ... other middleware ...
    "iot_hub_shared.auth_kit.middleware.JWTAuthMiddleware",  # must be last
]

AUTH_KIT_JWKS_URI = config("AUTH_KIT_JWKS_URI")
AUTH_KIT_CACHE_TTL = config("AUTH_KIT_CACHE_TTL", default=3600, cast=int)
```

> `JWTAuthMiddleware` must come **after** Django's built-in
> `AuthenticationMiddleware`. If placed before it, `AuthenticationMiddleware`
> will overwrite `request.user` with `AnonymousUser` and silently bypass
> authentication.

### Step 4 — Protect views

```python
from iot_hub_shared.auth_kit.middleware import login_required, role_required
from django.utils.decorators import method_decorator
from django.views import View

# Require any valid, non-expired token
@method_decorator(login_required, name="dispatch")
class MyView(View):
    def get(self, request):
        user_id = request.user.id         # int  — JWT "sub" cast to int
        role    = request.user.role       # str  — "admin" or "client"
        jti     = request.user.token_jti  # str  — unique token ID
        ...

# Require a specific role (returns 403 if role does not match)
@method_decorator(role_required("admin"), name="dispatch")
class AdminOnlyView(View):
    ...

# Allow multiple roles
@method_decorator(role_required("admin", "operator"), name="dispatch")
class PrivilegedView(View):
    ...
```

### How it works end-to-end

```
Incoming request
  │
  ▼
JWTAuthMiddleware
  ├─ No Authorization header → request.user = None
  ├─ Non-Bearer scheme       → request.user = None
  └─ Bearer token found:
       ├─ Decode header → read kid
       ├─ Lookup public key in local cache
       │    └─ Cache miss → GET /api/auth/.well-known/jwks.json (once)
       ├─ Verify RS256 signature  ← no network call to auth-service
       ├─ Check exp claim
       ├─ Valid → request.user = AuthenticatedUser(id, role, token_jti)
       └─ Any failure → request.user = None
  │
  ▼
View decorator
  ├─ @login_required:   request.user is None → 401 Unauthorized
  ├─ @role_required:    wrong role → 403 Forbidden
  └─ passes → view executes normally
```

---

## Running Tests

```bash
# From the auth-service root
pip install -r requirements.txt
pytest
```

The test suite uses SQLite in-memory. `BUILD_TIME=1` is hard-set in
`src/conftest.py` before Django loads, which switches the database backend so no
running PostgreSQL instance is required.

```bash
pytest --cov=apps --cov-report=term-missing          # with coverage report
pytest src/apps/users/tests/test_token_service.py -v # single module
pytest src/apps/users/tests/test_login_view.py -v    # login view tests
```

---

## User Model & Roles

The service uses a custom `User` model (`AUTH_USER_MODEL = "users.User"`)
extending Django's `AbstractBaseUser` and `PermissionsMixin`.

```
users table
┌─────────────┬──────────────┬───────────────────────────────────┐
│ Field       │ Type         │ Notes                             │
├─────────────┼──────────────┼───────────────────────────────────┤
│ id          │ AutoField    │ Integer PK — becomes JWT "sub"    │
│ username    │ CharField    │ Unique. Used for login.           │
│ email       │ EmailField   │ Unique.                           │
│ role        │ CharField    │ "admin" or "client"               │
│ is_staff    │ BooleanField │ Django admin access               │
│ is_active   │ BooleanField │ Soft-disable without deleting     │
│ created_at  │ DateTime     │ Auto-set on creation              │
│ updated_at  │ DateTime     │ Auto-updated on save              │
└─────────────┴──────────────┴───────────────────────────────────┘
```

| Role | JWT `role` claim | Intended use |
|---|---|---|
| `admin` | `"admin"` | Internal tooling, admin dashboards, privileged operations |
| `client` | `"client"` | End-user-facing APIs |

---

## Configuration Reference

All settings are read via `python-decouple` from the `.env` file. See
`.env.example` for a fully annotated template.

| Variable | Required | Default | Description |
|---|---|---|---|
| `SECRET_KEY` | Yes | — | Django cryptographic secret |
| `DEBUG` | No | `false` | Django debug mode |
| `ALLOWED_HOSTS` | Yes | — | Comma-separated hostnames. Must include `auth-service` for inter-container communication on `iot-hub-nw`. |
| `DB_HOST` | Yes | — | Postgres hostname (`postgres` in workspace, `auth-db` in standalone) |
| `DB_PORT` | No | `5432` | Postgres port |
| `DB_NAME` | Yes | — | Database name |
| `DB_USER` | Yes | — | Database user |
| `DB_PASSWORD` | Yes | — | Database password |
| `JWT_PRIVATE_KEY_PATH` | Yes | — | Path to RSA private key PEM file inside container |
| `JWT_PUBLIC_KEY_PATH` | Yes | — | Path to RSA public key PEM file inside container |
| `JWT_ACCESS_TOKEN_TTL_SECONDS` | No | `3600` | Token lifetime in seconds |
| `JWT_KEY_ID` | No | `auth-service-key-1` | `kid` header embedded in every issued token |
| `AUTH_SERVICE_PORT` | No | `8001` | Host port mapped to the container |
| `ALLOW_SETUP_ADMIN` | No | `false` | Set `true` to auto-seed dev users on container startup |
| `DEV_SUPERUSER_PASSWORD` | Conditional | — | Required when `ALLOW_SETUP_ADMIN=true` |
| `DEV_ADMIN_PASSWORD` | No | — | If unset, `admin_user` seed is skipped silently |
| `DEV_CLIENT_PASSWORD` | No | — | If unset, `client_user` seed is skipped silently |
| `CORS_ALLOW_ALL_ORIGINS` | No | `false` | Set `true` only for local development |
| `CORS_ALLOWED_ORIGINS` | No | — | Comma-separated list of allowed CORS origins |
