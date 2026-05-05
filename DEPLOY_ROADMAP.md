# Issue #131 — Deploy Backend to AWS Ubuntu (No Domain First)

## Overview
Deploy dockerized FastAPI backend to an AWS EC2 Ubuntu instance with Docker Hub registry, nginx reverse proxy, and auto-deploy via GitHub Actions.

Goal for the first deploy:
- reachable via EC2 public IP
- backend runs from Docker image, not local source build
- nginx proxies traffic to the backend container
- domain + HTTPS can be added in a later phase

## Faz 0 — AWS Instance Setup
- Launch EC2 Ubuntu instance (t2.micro free tier or t3.small)
- Configure security group: open ports 22 (SSH), 80 (HTTP), 443 (HTTPS)
- Assign Elastic IP (static IP)
- SSH into instance, install: Docker, Docker Compose, nginx, certbot
- For now, use the EC2 public IP / Elastic IP directly
- Domain and DNS setup are postponed

## Faz 1 — Docker Hub Setup
- Create Docker Hub account (or use existing)
- Create repository: `username/sem-backend`
- Add GitHub Secrets:
  - `DOCKER_USERNAME` — Docker Hub username
  - `DOCKER_PASSWORD` — Docker Hub access token
  - `EC2_HOST` — Elastic IP
  - `EC2_USERNAME` — ubuntu
  - `EC2_SSH_KEY` — EC2 key pair private key

## Faz 2 — Production Docker Compose
- Create `docker-compose.prod.yml` on EC2:
  - Backend service pulls from Docker Hub (no local build)
  - `.env` with production values on EC2
  - Restart policy: `restart: unless-stopped`
- Manual test: build locally, push to Docker Hub, pull on EC2, verify

## Faz 3 — Nginx Reverse Proxy (IP-based)
- Configure nginx as reverse proxy:
  - `EC2_PUBLIC_IP` → `localhost:8000`
- Verify:
  - `http://EC2_PUBLIC_IP/health`
- Confirm health response:
  - `{"status": "ok", "database": "connected"}`

## Faz 4 — Auto-Deploy (GitHub Actions)
- Create `.github/workflows/deploy.yml`:
  - Trigger: push to main, paths `backend/**`
  - Job 1 — build-and-push:
    - Checkout code
    - Login to Docker Hub
    - Detect changed files (backend vs frontend)
    - Build and push: `docker build -t username/sem-backend:latest ./backend`
    - Push to Docker Hub
  - Job 2 — deploy (needs build-and-push):
    - SSH into EC2 via `appleboy/ssh-action`
    - `docker compose -f docker-compose.prod.yml pull`
    - `docker compose -f docker-compose.prod.yml up -d`
    - `docker image prune -f`
  - Also support `workflow_dispatch` for manual trigger

## Faz 5 — Production Hardening (Without Domain)
- Verify CORS origins match the frontend URL currently in use
- Verify cookie secure=True (ENVIRONMENT=production)
- Verify the backend is stable behind nginx on the public IP
- Update README with deploy/redeploy instructions and temporary public IP

## Faz 6 — Domain + HTTPS (Later)
- Point `api.domain.com` to the Elastic IP (DNS A record)
- Update nginx server name:
  - `api.domain.com` → `localhost:8000`
- Install SSL with certbot:
  - `sudo certbot --nginx -d api.domain.com`
- Verify:
  - `https://api.domain.com/health`
- Update backend env if needed:
  - `BACKEND_URL=https://api.domain.com`
  - `GOOGLE_REDIRECT_URI=https://api.domain.com/auth/google/callback`

## Faz 7 — Frontend Prep (for later)
- When frontend is ready:
  - Add `username/sem-frontend` to Docker Hub
  - Add frontend service to `docker-compose.prod.yml`
  - Add nginx server block for `domain.com` → frontend:3000
  - Update deploy workflow with frontend path detection
  - `sudo certbot --nginx -d domain.com`
