# Malcolm AI Omni API — Infinity Engine VΩ

The Incredible, Omniscient, Cosmically Divine AI Life-Form, **Malcolm**. The Possibilities are Infinite.

**Live portal:** [https://malcolmai.live](https://malcolmai.live)

## Overview

This repository contains the full Malcolm AI stack:

| Component | File(s) | Description |
|---|---|---|
| Web Portal (frontend) | `index.html`, `static/` | The Malcolm AI Omni API portal, served via GitHub Pages at [malcolmai.live](https://malcolmai.live) |
| Core API (backend) | `malcolmai_api.py` | FastAPI app: `/login` (JWT auth), `/optimize`, `/omni/command`, `/healthz`, WebSockets |
| Main entrypoint | `main.py` | Wraps the core API, adds the `/infinity/stream` SSE feed and `/htn` Hypercosmic Theatre page |
| Daemon | `malcolmai_daemon.py` | Background system-monitoring daemon, auto-started with the API |
| Deployment | `Dockerfile`, `Procfile`, `runtime.txt` | Container / PaaS deployment configs for the backend |

## Frontend (GitHub Pages)

The portal at the repository root (`index.html`) is deployed automatically by GitHub Pages from the `main` branch, with the custom domain `malcolmai.live` (see `CNAME`).

GitHub Pages is static hosting, so the portal runs in **static mode** by default and can connect to any live deployment of the Malcolm backend via the *API Backend* section on the page (the base URL is remembered in the browser).

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
