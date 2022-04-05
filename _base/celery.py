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
        'schedule': 20,
        'options': {
            'queue': 'trx_network_consumer',
            'expire': 20
        },
    },
    'bsc_network_consumer': {
        'task': 'tracker.tasks.bsc_network_consumer',
        'schedule': 15,
        'options': {
            'queue': 'bsc_network_consumer',
            'expire': 15
        },
    },
    # 'eth_network_consumer': {
    #     'task': 'tracker.tasks.eth_network_consumer',
    #     'schedule': 30,
    #     'options': {
    #         'queue': 'eth_network_consumer',
    #         'expire': 39
    #     },
    # },
    'add_block_infos': {
        'task': 'tracker.tasks.add_block_infos',
        'schedule': 10,
        'options': {
            'queue': 'transfer',
            'expire': 10
        },
    },
    'create_withdraw_transaction': {
        'task': 'ledger.tasks.withdraw.create_transaction_from_not_broadcasts',
        'schedule': 10,
        'options': {
            'queue': 'transfer',
            'expire': 10
        },
    },
    'coin_market_cap_update': {
        'task': 'collector.tasks.coin_market_cap.update_coin_market_cap',
        # 'schedule': crontab(minute=0, hour=2),
        'schedule': crontab(minute="*/30"),
    },
    'update_network_fee': {
        'task': 'ledger.tasks.fee.update_network_fees',
        'schedule': crontab(minute="*/30"),
        'options': {
            'queue': 'celery',
            'expire': 30 * 60
        },
    },
    'update_binance_withdraw': {
        'task': 'ledger.tasks.withdraw.update_binance_withdraw',
        'schedule': 10,
        'options': {
            'queue': 'binance',
            'expire': 10
        },
    },
    'inject_tether_to_futures': {
        'task': 'provider.tasks.binance.inject_tether_to_futures',
        'schedule': 1,
        'options': {
            'queue': 'binance-monitor',
            'expire': 1
        },
    },
    'collect_metrics': {
        'task': 'collector.tasks.metrics.collect_metrics',
        'schedule': 5,
        'options': {
            'queue': 'metrics',
            'expire': 5
        },
    },
    'monitor_values': {
        'task': 'collector.tasks.monitor.collect_values',
        'schedule': 300,
        'options': {
            'queue': 'celery',
            'expire': 300
        },
    },
    'monitor_blockchain_delays': {
        'task': 'tracker.tasks.monitor_blockchain_delays',
        'schedule': 30,
        'options': {
            'queue': 'celery',
            'expire': 30
        },
    },
    'fill_future_binance_income': {
        'task': 'collector.tasks.binance.fill_future_binance_income',
        'schedule': crontab(minute=5),
        'options': {
            'queue': 'binance',
            'expire': 3600
        },
    },
    'auto_hedge_assets': {
        'task': 'provider.tasks.auto_hedge.auto_hedge_assets',
        'schedule': crontab(hour=1, minute=30),
        'options': {
            'queue': 'binance',
            'expire': 36000
        },
    },
    'lock_monitor': {
        'task': 'ledger.tasks.lock_monitor.lock_monitor',
        'schedule': crontab(minute=0),
        'options': {
            'queue': 'celery',
            'expire': 3600
        },
    },
}
