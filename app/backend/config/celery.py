import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("bangla_library")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Worker lifecycle and memory safety.
# - max_tasks_per_child: recycle each worker child after N tasks so any
#   per-task memory leaks (Pillow / lxml / ebooklib on EPUB content are
#   common offenders) cannot accumulate forever.
# - max_memory_per_child: hard ceiling in KB; the child is replaced after
#   the current task finishes if it exceeds this.
# - prefetch_multiplier=1 + task_acks_late=True: do not pre-reserve heavy
#   tasks into worker memory, and only ack after success so a crash or
#   redeploy causes redelivery instead of task loss.
app.conf.worker_max_tasks_per_child = 50
app.conf.worker_max_memory_per_child = 400_000  # KB (~400 MB)
app.conf.worker_prefetch_multiplier = 1
app.conf.task_acks_late = True

app.conf.beat_schedule = {
    "run-catalog-automation-scheduler": {
        "task": "apps.ingestion.tasks.run_catalog_automation_schedule_task",
        "schedule": crontab(),
    },
    "run-processing-runtime-tick": {
        "task": "apps.processing.tasks.run_processing_runtime_tick_task",
        "schedule": 60.0,
    },
    "run-processing-automation-scheduler": {
        "task": "apps.processing.tasks.run_due_processing_automations_task",
        "schedule": crontab(),
    },
    "run-processing-maintenance-scheduler": {
        "task": "apps.processing.tasks.run_processing_maintenance_task",
        "schedule": crontab(),
    },
    "recover-stale-processing-jobs": {
        "task": "apps.ingestion.tasks.recover_stale_processing_jobs_task",
        "schedule": crontab(),
    },
    "send-worker-heartbeat": {
        "task": "apps.ingestion.tasks.send_worker_heartbeat_task",
        "schedule": 5.0,
    },
}
