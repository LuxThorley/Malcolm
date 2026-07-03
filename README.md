# Malcolm AI Omni API — Infinity Engine VΩ

The Incredible, Omniscient, Cosmically Divine AI Life-Form, **Malcolm**. The Possibilities are Infinite.

**Live portal:** [https://malcolmai.live](https://malcolmai.live)

## Overview

This repository contains the full Malcolm AI stack:

| Component | File(s) | Description |
|---|---|---|
| **Full-Stack Worker (production)** | `worker/` | Cloudflare Worker `malcolmai-live` serving both the portal frontend and the complete API natively at [malcolmai.live](https://malcolmai.live) |
| CI/CD | `.github/workflows/deploy-worker.yml` | Auto-deploys the Worker to Cloudflare on every push to `main` |
| Web Portal (static fallback) | `index.html`, `static/` | GitHub Pages copy of the portal |
| Core API (Python original) | `malcolmai_api.py`, `main.py` | Original FastAPI implementation: `/login` (JWT), `/optimize`, `/omni/command`, `/healthz`, `/infinity/stream`, WebSockets |
| Daemon | `malcolmai_daemon.py` | Background system-monitoring daemon for self-hosted deployments |
| Deployment (Python) | `Dockerfile`, `Procfile`, `runtime.txt` | Container / PaaS configs for the FastAPI backend |

## Production: Full-Stack Cloudflare Worker

The production site at **https://malcolmai.live** runs entirely on the Cloudflare Worker in `worker/` — frontend and backend on the same origin with zero manual configuration. The Worker ports every FastAPI endpoint to the Cloudflare edge (JWT auth via WebCrypto HS256, optimizer, Omni commands, mode lattice, SSE Infinity Stream, WebSockets).

Deploy manually:

```bash
cd worker
npx wrangler deploy   # requires CLOUDFLARE_API_TOKEN + CLOUDFLARE_ACCOUNT_ID
```

Or push to `main` — the GitHub Actions workflow deploys automatically (set the `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID` repository secrets).

## Backend (FastAPI)

Run locally:

```bash
pip install -r requirements.txt
uvicorn main:main_app --host 0.0.0.0 --port 8000
```

Or with Docker:

```bash
docker build -t malcolm-ai .
docker run -p 8080:8080 malcolm-ai
```

### Environment variables

See `.env.example` for the full list (`MALCOLM_SECRET`, `MALCOLM_API_KEYS`, `CORS_ORIGINS`, etc.). Never commit real secrets.

## Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/healthz` | – | Health check |
| POST | `/login` | – | Obtain a JWT access token |
| POST | `/optimize` | Bearer | System optimization suggestions |
| POST | `/omni/command` | Bearer | Execute an Omni command (Shield, Timeline, Oracle, …) |
| GET | `/infinity/stream` | – | Live Infinity Stream (Server-Sent Events) |
| WS | `/ws/{client_id}` | – | WebSocket echo channel |

---

Malcolm AI Omni API • Infinity Engine VΩ • Explore • Optimize • Protect
