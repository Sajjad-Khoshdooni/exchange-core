import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_base.settings')

app = Celery('exchange_core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.task_routes = {
    'tracker.tasks.trx_network_consumer': {'queue': 'trx_network_consumer'},
}

app.conf.beat_schedule = {
    'trx_network_consumer': {
        'task': 'tracker.tasks.trx_network_consumer',
        'schedule': 60,
    },
}
