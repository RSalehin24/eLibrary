import os

bind = "0.0.0.0:8000"
workers = int(os.environ.get("API_WORKERS", "4"))
threads = int(os.environ.get("API_THREADS", "4"))
worker_class = "gthread"
timeout = 30
graceful_timeout = 30
keepalive = 5
max_requests = 2000
max_requests_jitter = 200
accesslog = None
errorlog = "-"
capture_output = True
