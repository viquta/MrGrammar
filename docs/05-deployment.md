# Deployment & Infrastructure

This document describes the deployment architecture, Docker Compose configuration, and infrastructure setup of MrGrammar.

> **UML Diagram**: Open [`diagrams/component-deployment.drawio`](diagrams/component-deployment.drawio) in the Draw.io VS Code extension or at [diagrams.net](https://app.diagrams.net) to view the Component & Deployment diagram.
>
> ![Component & Deployment Diagram](diagrams/exported/component-deployment.png)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Docker Compose Services](#2-docker-compose-services)
3. [Port Mapping](#3-port-mapping)
4. [Environment Variables](#4-environment-variables)
5. [Volumes](#5-volumes)
6. [Dependency Chain](#6-dependency-chain)
7. [Container Details](#7-container-details)
8. [Network Architecture](#8-network-architecture)

---

## 1. Overview

MrGrammar runs as a set of four Docker containers orchestrated by Docker Compose:

| Service | Image | Purpose |
|---------|-------|---------|
| **frontend** | Custom (Node 22-alpine) | SvelteKit SPA development server |
| **backend** | Custom (Python 3.12-slim) | Django REST Framework API server |
| **db** | `postgres:16-alpine` | PostgreSQL relational database |
| **languagetool** | `erikvl87/languagetool` | Self-hosted grammar checker (German) |

All services communicate over a shared Docker Compose network. The frontend and backend expose ports to the host for browser access and API calls.

---

## 2. Docker Compose Services

### `db` — PostgreSQL Database

| Property | Value |
|----------|-------|
| Image | `postgres:16-alpine` |
| Host port | `5432` |
| Container port | `5432` |
| Volume | `pgdata:/var/lib/postgresql/data` |

Initialises with the database `mrgrammar`, user `mrgrammar`, and password `mrgrammar_dev`. These defaults are suitable for local development only.

### `languagetool` — Grammar Checker

| Property | Value |
|----------|-------|
| Image | `erikvl87/languagetool` |
| Host port | `8010` |
| Container port | `8010` |
| JVM min heap | 256 MB |
| JVM max heap | 512 MB |

Provides the `/v2/check` REST endpoint for German grammar and spell checking. The backend's `nlp` app calls this service during text analysis.

### `backend` — Django API Server

| Property | Value |
|----------|-------|
| Build context | `.` (project root) |
| Dockerfile | `Dockerfile.backend` |
| Host port | `8000` |
| Container port | `8000` |
| Depends on | `db`, `languagetool` |
| Volume mounts | `.:/app` (code hot-reload) |

Runs the Django development server. On startup, the container installs Python dependencies from `requirements.txt` and serves the API at `http://localhost:8000/api/`.

### `frontend` — SvelteKit SPA

| Property | Value |
|----------|-------|
| Build context | `./frontend` |
| Dockerfile | `frontend/Dockerfile` |
| Host port | `5173` |
| Container port | `5173` |
| Depends on | `backend` |
| Volume mounts | `./frontend:/app`, `/app/node_modules` (isolated) |

Runs the Vite development server with `--host 0.0.0.0` for container access. Node modules are isolated in an anonymous volume to prevent host/container conflicts.

---

## 3. Port Mapping

| Service | Host Port | Container Port | Protocol | Purpose |
|---------|-----------|---------------|----------|---------|
| frontend | 5173 | 5173 | HTTP | SvelteKit dev server (browser access) |
| backend | 8000 | 8000 | HTTP | Django REST API |
| db | 5432 | 5432 | PostgreSQL | Database connections |
| languagetool | 8010 | 8010 | HTTP | LanguageTool REST API |

---

## 4. Environment Variables

### Backend Service

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DEBUG` | `True` | Enable Django debug mode |
| `POSTGRES_DB` | `mrgrammar` | Database name |
| `POSTGRES_USER` | `mrgrammar` | Database user |
| `POSTGRES_PASSWORD` | `mrgrammar_dev` | Database password |
| `POSTGRES_HOST` | `db` | Database hostname (Docker service name) |
| `POSTGRES_PORT` | `5432` | Database port |
| `LANGUAGETOOL_URL` | `http://languagetool:8010/v2` | LanguageTool API base URL |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Allowed CORS origins (comma-separated) |

### Frontend Service

| Variable | Default | Description |
|----------|---------|-------------|
| `PUBLIC_API_URL` | `http://localhost:8000/api` | Backend API base URL for browser requests |

### Database Service

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_DB` | `mrgrammar` | Database to create on first run |
| `POSTGRES_USER` | `mrgrammar` | Superuser name |
| `POSTGRES_PASSWORD` | `mrgrammar_dev` | Superuser password |

### LanguageTool Service

| Variable | Default | Description |
|----------|---------|-------------|
| `Java_Xms` | `256m` | JVM minimum heap size |
| `Java_Xmx` | `512m` | JVM maximum heap size |

---

## 5. Volumes

| Volume | Type | Mount Point | Purpose |
|--------|------|-------------|---------|
| `pgdata` | Named volume | `/var/lib/postgresql/data` | Persists database data across container restarts |
| `.:/app` | Bind mount (backend) | `/app` | Hot-reloads Python code changes during development |
| `./frontend:/app` | Bind mount (frontend) | `/app` | Hot-reloads Svelte/TS code changes during development |
| `/app/node_modules` | Anonymous volume (frontend) | `/app/node_modules` | Isolates container node_modules from host |

---

## 6. Dependency Chain

```
frontend ──depends_on──→ backend ──depends_on──→ db
                                  ──depends_on──→ languagetool
```

Docker Compose starts services in dependency order:

1. **db** and **languagetool** start first (no dependencies)
2. **backend** starts after db and languagetool are running
3. **frontend** starts after backend is running

> **Note**: `depends_on` only waits for the container to start, not for the service inside it to be ready. In production, health checks or wait scripts should be used to ensure PostgreSQL and LanguageTool are accepting connections before the backend begins serving requests.

---

## 7. Container Details

### Backend Dockerfile (`Dockerfile.backend`)

| Stage | Action |
|-------|--------|
| Base image | `python:3.12-slim` |
| System deps | `libpq-dev`, `gcc` (for psycopg2 compilation) |
| Python deps | `pip install -r requirements.txt` |
| Working dir | `/app` |
| Exposed port | `8000` |
| CMD | `python manage.py runserver 0.0.0.0:8000` |

### Frontend Dockerfile (`frontend/Dockerfile`)

| Stage | Action |
|-------|--------|
| Base image | `node:22-alpine` |
| Package install | `npm install` |
| Working dir | `/app` |
| Exposed port | `5173` |
| CMD | `npm run dev -- --host 0.0.0.0` |

---

## 8. Network Architecture

All four services share a single Docker Compose default network. Inter-service communication uses Docker DNS resolution (service names as hostnames):

```
┌──────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                      │
│                                                                │
│  ┌──────────┐     HTTP/JSON     ┌──────────┐                 │
│  │ frontend │ ───────────────→  │ backend  │                 │
│  │  :5173   │   port 8000       │  :8000   │                 │
│  └──────────┘                   └────┬──┬──┘                 │
│                                      │  │                     │
│                           PostgreSQL │  │ HTTP                │
│                           port 5432  │  │ port 8010           │
│                                      ▼  ▼                     │
│                              ┌──────┐  ┌─────────────┐       │
│                              │  db  │  │ languagetool │       │
│                              │ :5432│  │   :8010      │       │
│                              └──────┘  └─────────────┘       │
│                                 │                              │
│                              ┌──┴──┐                          │
│                              │pgdata│ (volume)                │
│                              └─────┘                          │
└──────────────────────────────────────────────────────────────┘
                        │              │
              Host :5173, :8000    Host :5432, :8010
              (browser access)    (development access)
```

### Communication Protocols

| From | To | Protocol | Endpoint |
|------|-----|----------|----------|
| Browser | Frontend | HTTP | `localhost:5173` |
| Frontend (browser) | Backend | HTTP/JSON | `localhost:8000/api/` |
| Backend | Database | PostgreSQL wire protocol | `db:5432` |
| Backend (nlp) | LanguageTool | HTTP | `languagetool:8010/v2/check` |

> **CORS**: The backend includes `django-cors-headers` middleware configured to accept requests from `http://localhost:5173` (the frontend's origin). This is required because the browser makes cross-origin API calls from the SvelteKit dev server to the Django API server.
