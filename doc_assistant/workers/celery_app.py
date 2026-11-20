"""
Celery application configuration for the AI Document Assistant.

Creates and configures the Celery app with Redis broker/backend,
JSON serialization, task routing, retry policies, and timeouts.
"""

from __future__ import annotations

import os

from celery import Celery

# ---------------------------------------------------------------------------
# Broker & backend URLs – sourced from env vars with sensible defaults
# ---------------------------------------------------------------------------
REDIS_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
REDIS_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

# ---------------------------------------------------------------------------
# App instantiation
# ---------------------------------------------------------------------------
celery_app = Celery(
    "doc_assistant",
    broker=REDIS_BROKER_URL,
    backend=REDIS_RESULT_BACKEND,
    include=[
        "doc_assistant.workers.document_worker",
    ],
)

# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------
celery_app.conf.accept_content = ["json"]
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"

# ---------------------------------------------------------------------------
# Worker behaviour
# ---------------------------------------------------------------------------
# Acknowledge messages *after* the task has completed (not before), so that
# if a worker crashes mid-task the message is re-delivered.
celery_app.conf.task_acks_late = True

# Fetch only one task at a time per worker process so that long-running
# document-processing jobs don't starve other workers.
celery_app.conf.worker_prefetch_multiplier = 1

# ---------------------------------------------------------------------------
# Task routing
# ---------------------------------------------------------------------------
celery_app.conf.task_routes = {
    "doc_assistant.workers.document_worker.process_document": {
        "queue": "document_processing",
    },
}

# ---------------------------------------------------------------------------
# Default retry policy (applied when a task calls self.retry() without
# overriding these values).
# ---------------------------------------------------------------------------
celery_app.conf.task_default_retry_delay = 30  # seconds between retries
celery_app.conf.task_max_retries = 3           # max automatic retries

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# Hard time limit kills the worker process after this many seconds.
celery_app.conf.task_time_limit = 600  # 10 minutes

# Soft time limit raises SoftTimeLimitExceeded so the task can clean up.
celery_app.conf.task_soft_time_limit = 540  # 9 minutes

# How long to wait for a result before timing out (get / AsyncResult).
celery_app.conf.result_expires = 3600  # 1 hour

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
celery_app.conf.worker_hijack_root_logger = False  # keep our own logging
celery_app.conf.task_track_started = True
celery_app.conf.task_reject_on_worker_lost = True
celery_app.conf.broker_connection_retry_on_startup = True
