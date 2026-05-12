# Social Event Mapper

Social Event Mapper is a multi-platform event discovery and hosting project built for CMPE 354. It includes:

- a FastAPI backend for authentication, event management, media, comments, invites, notifications, and profiles
- a Next.js web frontend for discovery, event hosting, profile flows, and invite handling
- an Android mobile app built with Kotlin and Jetpack Compose

This README is the main entry point for setting up the repository locally. It consolidates the essential commands, environment files, and build instructions needed to run the project by hand.

**Live deployment:** https://thesocialeventmapper.social

## Default Test Credentials

Two pre-created accounts are available on the live deployment for immediate testing:

| Account | Email | Password |
|---------|-------|----------|
| User 1 | `mehmet.kaya.demo@gmail.com` | `Demo1234!` |
| User 2 | `emir.demir.demo@gmail.com`  | `Demo1234!` |

## Repository Structure

```text
.
├── backend/                 FastAPI application, tests, and backend docs
├── frontend/                Next.js web app and frontend docs
├── mobile/                  Android app (Kotlin + Jetpack Compose)
├── deploy/                  EC2 and nginx deployment helpers
├── design/                  Design references and mockups
├── docker-compose.yml       Local Docker Compose for backend development
├── docker-compose.prod.yml  Production Docker Compose reference
└── .github/workflows/       CI and deployment workflows
```

## Tech Stack

- Backend: Python 3.12, FastAPI, Supabase, JWT auth, Pillow, Ruff, Pytest
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS, Vitest
- Mobile: Kotlin, Jetpack Compose, Retrofit, OkHttp, MapLibre
- Infra: Docker, Docker Compose, GitHub Actions, nginx, EC2

## What Is Already Automated

The repository already contains:

- backend CI: [.github/workflows/backend-ci.yml](./.github/workflows/backend-ci.yml)
- frontend CI: [.github/workflows/frontend-ci.yml](./.github/workflows/frontend-ci.yml)
- Android CI (lint + unit tests on PRs): [.github/workflows/android-ci.yml](./.github/workflows/android-ci.yml)
- Android APK build workflow: [.github/workflows/android-build.yml](./.github/workflows/android-build.yml)
- production deploy pipeline for backend and frontend Docker images: [.github/workflows/deploy.yml](./.github/workflows/deploy.yml)

Current automation coverage:

- backend CI runs lint and backend test shards on pull requests
- frontend CI runs type check, lint, and Vitest suite on pull requests
- Android CI runs detekt and unit tests on pull requests touching `mobile/`
- Android APK workflow builds a debug APK on every push to `main`
- the same Android workflow attaches the APK to a GitHub release when a release is created
- production deploy workflow builds and deploys backend and frontend Docker images on pushes to `main`

## Prerequisites

Install the tools that match the parts you want to run:

- Docker and Docker Compose
- Python 3.12 and `pip` if you want to run the backend without Docker
- Node.js 22 and npm for the frontend
- Android Studio, Android SDK, an emulator or physical Android device for mobile
- JDK 17 for Android/Gradle CLI builds

## Environment Files

Two local environment files are required for normal web/backend development:

- `backend/.env`
- `frontend/.env.local`

Copy them from the examples:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local
```

### Backend Environment Variables

Use [backend/.env.example](./backend/.env.example) as the source of truth.

Minimum local values:

| Variable | Example local value | Notes |
|---|---|---|
| `SUPABASE_URL` | `https://xxxxx.supabase.co` | From Supabase project settings |
| `SUPABASE_KEY` | `eyJhbGci...` | Use the service role key for backend access |
| `JWT_SECRET` | `minimum-32-karakter-guvenli-secret` | Generate a strong random secret |
| `GOOGLE_CLIENT_ID` | `xxxxx.apps.googleusercontent.com` | Optional unless testing Google OAuth |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-xxxxx` | Optional unless testing Google OAuth |
| `GOOGLE_REDIRECT_URI` | `http://localhost:8888/auth/google/callback` | Local OAuth callback |
| `SMTP_HOST` | `smtp.gmail.com` | Needed for email flows |
| `SMTP_PORT` | `587` | Gmail app-password setup is expected |
| `SMTP_USER` | `your-email@gmail.com` | Sender account |
| `SMTP_PASSWORD` | `your-app-password` | App password, not your normal Gmail password |
| `SMTP_FROM_EMAIL` | `noreply@yourdomain.com` | Outgoing sender address |
| `SMTP_FROM_NAME` | `Social Event Mapper` | Outgoing sender name |
| `ENVIRONMENT` | `development` | Local development mode |
| `FRONTEND_URL` | `http://localhost:3000` | Used in email and OAuth redirects |
| `BACKEND_URL` | `http://localhost:8888` | Public backend base URL |
| `CORS_ORIGINS` | `http://localhost:3000` | Frontend origin allowed by backend |

### Frontend Environment Variables

Use [frontend/.env.example](./frontend/.env.example) as the source of truth.

| Variable | Example local value | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8888` | Backend base URL used by the Next.js app |

### Mobile Local API Configuration

The mobile app currently does **not** use a separate `.env` file. Its API base URL is defined in:

- [mobile/app/src/main/java/com/bounswe/group9/mobile/data/remote/RetrofitProvider.kt](./mobile/app/src/main/java/com/bounswe/group9/mobile/data/remote/RetrofitProvider.kt)

For local testing:

- Android emulator: use `http://10.0.2.2:8888/`
- Physical device on the same network: use `http://<YOUR_COMPUTER_LAN_IP>:8888/`

Do **not** use `localhost` from the Android emulator, because the emulator sees its own loopback interface instead of your machine.

## Data Seeding

The live deployment at `https://thesocialeventmapper.social` is already fully seeded with predefined categories and sample content — use the default credentials above to log in and test immediately without any setup.

If you are connecting a **fresh Supabase instance**, run the following SQL in the [Supabase SQL Editor](https://supabase.com/dashboard) to populate the predefined categories:

```sql
INSERT INTO categories (name, is_predefined, is_approved) VALUES
  ('Arts & Culture',   true, true),
  ('Business',         true, true),
  ('Community',        true, true),
  ('Education',        true, true),
  ('Family',           true, true),
  ('Film & Media',     true, true),
  ('Food & Drink',     true, true),
  ('Gaming',           true, true),
  ('Health & Wellness',true, true),
  ('Music',            true, true),
  ('Nightlife',        true, true),
  ('Outdoor',          true, true),
  ('Sports',           true, true),
  ('Technology',       true, true),
  ('Travel',           true, true)
ON CONFLICT (name) DO NOTHING;
```

## Local Development Quick Start

The fastest way to run the full web application locally (backend + frontend together):

```bash
cp backend/.env.example backend/.env   # fill in your values first
docker compose up --build
```

This starts:
- Backend API at [http://localhost:8888](http://localhost:8888) (Swagger: [/docs](http://localhost:8888/docs))
- Web frontend at [http://localhost:3000](http://localhost:3000)

For mobile, point the app to `http://10.0.2.2:8888/` (emulator) or your LAN IP (physical device) as described in the Mobile section.

## Backend

Detailed backend notes live in [backend/README.md](./backend/README.md).

### Run Backend Only with Docker Compose

```bash
docker compose up --build backend
```

Useful URLs:

- API base: [http://localhost:8888](http://localhost:8888)
- Swagger docs: [http://localhost:8888/docs](http://localhost:8888/docs)
- Health check: [http://localhost:8888/health](http://localhost:8888/health)

### Run Backend Without Docker

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8888 --reload
```

### Backend Docker Build

If you want to build the backend image directly:

```bash
docker build -t sem-backend ./backend
docker run --rm -p 8888:8000 --env-file backend/.env sem-backend
```

### Backend Verification

Run these from `backend/` if you are using a local Python environment:

```bash
ruff check .
pytest -v
```

If you started the backend through Docker Compose:

```bash
docker exec sem-backend ruff check .
docker exec sem-backend python -m pytest tests/ -v
```

## Frontend

Detailed frontend notes live in [frontend/README.md](./frontend/README.md).

### Run Frontend Locally

```bash
cd frontend
npm ci
npm run dev
```

Open:

- [http://localhost:3000](http://localhost:3000)

The frontend expects the backend to be running at the URL set in `NEXT_PUBLIC_API_BASE_URL`, and authenticated requests include cookies automatically.

### Frontend Production Build

```bash
cd frontend
npm run build
npm run start
```

### Frontend Docker Build

The frontend image requires a backend URL at build time:

```bash
docker build \
  --build-arg NEXT_PUBLIC_API_BASE_URL=http://localhost:8888 \
  -t sem-frontend \
  ./frontend

docker run --rm -p 3000:3000 sem-frontend
```

### Frontend Verification

Run from `frontend/`:

```bash
npm run lint:ci
npm run typecheck
npm run test:run
npm run build
```

For the full frontend check pipeline:

```bash
npm run check
```

## Mobile

The mobile project is an Android app under [mobile/](./mobile).

### Local API URL for Emulator or Device

Before running the app locally, update:

- [mobile/app/src/main/java/com/bounswe/group9/mobile/data/remote/RetrofitProvider.kt](./mobile/app/src/main/java/com/bounswe/group9/mobile/data/remote/RetrofitProvider.kt)

Change:

```kotlin
const val BASE_URL = "https://api.thesocialeventmapper.social/"
```

To one of these:

```kotlin
const val BASE_URL = "http://10.0.2.2:8888/"
```

or

```kotlin
const val BASE_URL = "http://<YOUR_COMPUTER_LAN_IP>:8888/"
```

The Android manifest already enables cleartext traffic for local HTTP development in:

- [mobile/app/src/main/AndroidManifest.xml](./mobile/app/src/main/AndroidManifest.xml)

### Run Mobile with Android Studio

1. Open `mobile/` in Android Studio
2. Let Gradle sync complete
3. Start an Android emulator or connect a device
4. Make sure the backend is already running on port `8888`
5. Run the `app` configuration

### Build Mobile from CLI

From `mobile/`:

```bash
chmod +x gradlew
./gradlew assembleDebug
./gradlew installDebug
```

### Build an APK

To build a debug APK (this is what the GitHub Actions workflow also produces):

```bash
cd mobile
./gradlew assembleDebug
```

Expected output:

```text
mobile/app/build/outputs/apk/debug/app-debug.apk
```

This APK can be installed directly on any Android device with "Install from unknown sources" enabled in device settings.

> **Note:** Release builds (`assembleRelease`) require a signing keystore and are not needed for development or milestone evaluation. Use the debug APK above.

### Mobile Verification

From `mobile/`:

```bash
./gradlew test
./gradlew assembleDebug
```

### Mobile E2E Tests (Maestro)

Maestro flows live in [`mobile/maestro/`](./mobile/maestro/). They run against a live emulator or device with the app installed.

Install Maestro CLI:

```bash
curl -Ls "https://get.maestro.mobile.dev" | bash
```

Run all flows:

```bash
# Make sure an emulator is running and the app is installed first
maestro test mobile/maestro/
```

Run a single flow:

```bash
maestro test mobile/maestro/01_login.yaml
```

## Local End-to-End Verification

After starting the backend and frontend:

1. Open the web app at `http://localhost:3000`
2. Confirm the backend health endpoint responds at `http://localhost:8888/health`
3. Register or log in through the web app
4. Create or browse events
5. If testing mobile, confirm the app can reach the same backend URL

## Performance Tests (k6)

Load test scripts live in [`performance/`](./performance/). Install k6 from [k6.io](https://k6.io/docs/get-started/installation/) then run:

```bash
# Health & categories smoke (20 VUs, 30s)
k6 run performance/k6_health.js

# Discovery endpoint under load
k6 run --vus 10 --duration 30s performance/k6_discovery.js

# Auth login flow
k6 run performance/k6_auth.js
```

Override the target URL with `BASE_URL=http://localhost:8888 k6 run performance/k6_health.js`.

## Docker and Deployment Reference

This repository is already dockerized for backend and frontend:

- backend image: [backend/Dockerfile](./backend/Dockerfile)
- frontend image: [frontend/Dockerfile](./frontend/Dockerfile)
- local backend compose: [docker-compose.yml](./docker-compose.yml)
- production compose: [docker-compose.prod.yml](./docker-compose.prod.yml)

Short production reference only:

- deployment workflow: [.github/workflows/deploy.yml](./.github/workflows/deploy.yml)
- nginx configs: [deploy/nginx/](./deploy/nginx)
- EC2 helpers: [deploy/ec2/](./deploy/ec2)

For production environment values, see:

- [backend/.env.production.example](./backend/.env.production.example)
- [frontend/env.production.example](./frontend/env.production.example)

## Additional References

- Backend documentation: [backend/README.md](./backend/README.md)
- Frontend documentation: [frontend/README.md](./frontend/README.md)
- Design references: [design/](./design)
