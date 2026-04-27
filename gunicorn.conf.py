import multiprocessing
import os


def _calculate_workers() -> int:
    configured = os.environ.get('GUNICORN_WORKERS')
    if configured:
        return max(4, min(8, int(configured)))
    recommended = (multiprocessing.cpu_count() * 2) + 1
    return max(4, min(8, recommended))


bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:8000')
workers = _calculate_workers()
threads = int(os.environ.get('GUNICORN_THREADS', '2'))
timeout = int(os.environ.get('GUNICORN_TIMEOUT', '60'))
graceful_timeout = int(os.environ.get('GUNICORN_GRACEFUL_TIMEOUT', '30'))
keepalive = int(os.environ.get('GUNICORN_KEEPALIVE', '5'))
max_requests = int(os.environ.get('GUNICORN_MAX_REQUESTS', '1000'))
max_requests_jitter = int(os.environ.get('GUNICORN_MAX_REQUESTS_JITTER', '100'))
accesslog = '-'
errorlog = '-'
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')
