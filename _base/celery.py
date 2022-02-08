import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_base.settings')

app = Celery('exchange_core')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'trx_network_consumer': {
        'task': 'tracker.tasks.trx_network_consumer',
        'schedule': 60,
        'options': {
            'queue': 'trx_network_consumer',
            'expire': 60
        },
    },
    'bsc_network_consumer': {
        'task': 'tracker.tasks.bsc_network_consumer',
        'schedule': 60,
        'options': {
            'queue': 'bsc_network_consumer',
            'expire': 60
        },
    },
    'trx_add_block_info': {
        'task': 'tracker.tasks.trx_add_block_info',
        'schedule': 60,
        'options': {
            'queue': 'trx_network_consumer',
            'expire': 60
        },
    },
    'update_binance_transfers': {
        'task': 'ledger.tasks.withdraw.update_binance_withdraw',
        'schedule': 60,
        'options': {
            'queue': 'transfer',
            'expire': 60
        },
    },
    'create_withdraw_transaction': {
        'task': 'ledger.tasks.withdraw.create_transaction_from_not_broadcasts',
        'schedule': 120,
        'options': {
            'queue': 'transfer',
            'expire': 120
        },
    },
    'coin_market_cap_update': {
        'task': 'collector.tasks.coin_market_cap.update_coin_market_cap',
        # 'schedule': crontab(minute=0, hour=2),
        'schedule': crontab(minute="*/30"),
    },
}
