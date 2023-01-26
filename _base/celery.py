import os

from celery import Celery
from celery.schedules import crontab
from decouple import config
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', '_base.settings')

app = Celery('exchange_core', broker=config('RABBITMQ_URL', default='pyamqp://guest@localhost//'))

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

TASK_MULTIPLIER = 1

if settings.DEBUG_OR_TESTING_OR_STAGING:
    TASK_MULTIPLIER = 5

app.conf.beat_schedule = {

    'update_network_fee': {
        'task': 'ledger.tasks.fee.update_network_fees',
        'schedule': crontab(minute="*/30"),
        'options': {
            'queue': 'celery',
            'expire': 30 * 60
        },
    },
    'update_provider_withdraw': {
        'task': 'ledger.tasks.withdraw.update_provider_withdraw',
        'schedule': 10 * TASK_MULTIPLIER,
        'options': {
            'queue': 'transfer',
            'expire': 10 * TASK_MULTIPLIER
        },
    },

    'update_withdraws': {
        'task': 'ledger.tasks.withdraw.update_withdraws',
        'schedule': 10 * TASK_MULTIPLIER,
        'options': {
            'queue': 'transfer',
            'expire': 10 * TASK_MULTIPLIER
        },
    },

    # market tasks
    'create depth orders': {
        'task': 'market.tasks.market_maker.create_depth_orders',
        'schedule': 60 * TASK_MULTIPLIER,
        'options': {
            'queue': 'market',
            'expire': 60 * TASK_MULTIPLIER
        },
    },
    'update maker orders': {
        'task': 'market.tasks.market_maker.update_maker_orders',
        'schedule': 10 * TASK_MULTIPLIER,
        'options': {
            'queue': 'market',
            'expire': 10 * TASK_MULTIPLIER
        },
    },
    'handle open stop loss': {
        'task': 'market.tasks.stop_loss.handle_stop_loss',
        'schedule': 1 * TASK_MULTIPLIER,
        'options': {
            'queue': 'stop_loss',
            'expire': 1 * TASK_MULTIPLIER
        },
    },
    'create_stake_revenue': {
        'task': 'stake.tasks.stake_revenue.create_stake_revenue',
        'schedule': crontab(hour=19, minute=30),
        'options': {
            'queue': 'celery',
            'expire': 36000
        },
    },
    'complete_stake_requests': {
        'task': 'stake.tasks.stake_finish.finish_stakes',
        'schedule': crontab(hour=20, minute=0),
        'options': {
            'queue': 'celery',
            'expire': 36000
        },
    },

    # 'lock_monitor': {
    #     'task': 'ledger.tasks.lock_monitor.lock_monitor',
    #     'schedule': crontab(minute=0),
    #     'options': {
    #         'queue': 'celery',
    #         'expire': 3600
    #     },
    # },

    # 'check_margin_level': {
    #     'task': 'ledger.tasks.margin.check_margin_level',
    #     'schedule': 5 * TASK_MULTIPLIER,
    #     'options': {
    #         'queue': 'margin',
    #         'expire': 5 * TASK_MULTIPLIER
    #     },
    # },

    # 'retention_leads_to_signup': {
    #     'task': 'accounts.tasks.retention.retention_leads_to_signup',
    #     'schedule': 3600,
    #     'options': {
    #         'queue': 'retention',
    #         'expire': 3600
    #     },
    # },

    # 'retention_actions': {
    #     'task': 'accounts.tasks.retention.retention_actions',
    #     'schedule': 3600,
    #     'options': {
    #         'queue': 'retention',
    #         'expire': 3600
    #     },
    # },

    'update_withdraw_status': {
        'task': 'financial.tasks.withdraw.update_withdraw_status',
        'schedule': 300 * TASK_MULTIPLIER,
        'options': {
            'queue': 'finance',
            'expire': 300 * TASK_MULTIPLIER
        },
    },

    'handle_missing_payments': {
        'task': 'financial.tasks.gateway.handle_missing_payments',
        'schedule': 30 * TASK_MULTIPLIER,
        'options': {
            'queue': 'finance',
            'expire': 30 * TASK_MULTIPLIER
        },
    },

    'random_trader': {
        'task': 'trader.tasks.random_trader.random_trader',
        'schedule': 17 * TASK_MULTIPLIER,
        'options': {
            'queue': 'trader',
            'expire': 17 * TASK_MULTIPLIER
        }
    },
    'carrot_trader': {
        'task': 'trader.tasks.carrot_trader.carrot_trader',
        'schedule': 7 * TASK_MULTIPLIER,
        'options': {
            'queue': 'trader',
            'expire': 7 * TASK_MULTIPLIER
        }
    },

    'update_accounts_pnl': {
        'task': 'ledger.tasks.pnl.create_pnl_histories',
        'schedule': crontab(hour=20, minute=30),
        'options': {
            'queue': 'history',
        }
    },
    'create_snapshot': {
        'task': 'ledger.tasks.snapshot.create_snapshot',
        'schedule': crontab(minute='*/5'),
        'options': {
            'queue': 'history',
            'expire': 200
        }
    },
    # 'create_accounting_report': {
    #     'task': 'accounting.tasks.weekly_fiat_transfer.create_weekly_accounting_report',
    #     'schedule': crontab(hour=19, minute=30, day_of_week=6),
    #     'options': {
    #         'queue': 'celery',
    #         'expire': 36000
    #     },
    # },
    'trigger_variant_action': {
        'task': 'experiment.tasks.action_trigger.trigger_variant_action',
        'schedule': 300 * TASK_MULTIPLIER,
        'options': {
            'queue': 'celery',
            'expire': 300 * TASK_MULTIPLIER
        },
    },
}
