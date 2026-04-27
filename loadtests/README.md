# Locust Load Testing

This folder contains a Locust test profile for NFR-1.3 validation at 100 concurrent users.

## Run Against Production Compose Stack

1. Start production stack:

```bash
docker compose -f docker-compose.prod.yml up --build -d
```

2. Run headless Locust with 100 users:

```bash
docker run --rm \
  --network mrgrammar_default \
  -v "$PWD/loadtests":/mnt/locust \
  -e LOCUST_USERNAME=student1 \
  -e LOCUST_PASSWORD=student-password \
  -e LOCUST_STUDENT_ID=1 \
  locustio/locust:2.39.1 \
  -f /mnt/locust/locustfile.py \
  --host http://nginx \
  --headless -u 100 -r 20 -t 5m
```

3. Review summary output (requests/sec, p95 latency, failures).

## Notes

- `/healthz/` and `/` are always exercised.
- Authenticated endpoints are exercised only when credentials are provided.
- Increase run time (`-t`) for steadier p95 and error-rate measurements.
