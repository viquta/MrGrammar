# Changelog

All notable changes to MrGrammar are documented here.

## [0.0.7] — 2026-04-27

### NFR-1 Performance

- **NFR-1.1 — Async NLP**: Text analysis is now queued via Celery (broker: Redis). The submission endpoint returns immediately; the frontend polls for results, keeping p95 response time well under 2 s even under load.
- **NFR-1.2 — Caching**: Analytics dashboard endpoints are cached in Redis (TTL 300 s for student views, 120 s for classroom views), eliminating repeated DB aggregation queries.
- **NFR-1.3 — Concurrent-user capacity**: Production stack uses Nginx as a reverse proxy in front of two Gunicorn workers (`backend1`, `backend2`), validated to handle 100 concurrent users via `docker-compose.prod.yml`.
- **NFR-1.4 — Availability**: `/healthz` health-check endpoint added; Docker Compose restart policies (`unless-stopped`) keep all services running across restarts. Load balancer removes a failed backend automatically.

### Infrastructure

- Added `docker-compose.prod.yml` with services: `db`, `redis`, `languagetool`, `frontend`, `backend1`, `backend2`, `celery_worker`, `celery_beat`, `nginx`.
- Added database performance indexes on `Submission` and `DetectedError` tables (migrations `submissions/0003`, `feedback/0004`).

---

## [0.0.6] and earlier

No formal changelog kept. See git history.
