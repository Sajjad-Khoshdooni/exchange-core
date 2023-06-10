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
    'auto_clear_debts': {
        'task': 'ledger.tasks.debt.auto_clear_debts',
        'schedule': 60 * TASK_MULTIPLIER,
        'options': {
            'queue': 'celery',
            'expire': 60 * TASK_MULTIPLIER
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

    'create_stake_revenue': {
        'task': 'stake.tasks.stake_revenue.create_stake_revenue',
        'schedule': crontab(hour=22, minute=0),
        'options': {
            'queue': 'celery',
            'expire': 36000
        },
    },
    'complete_stake_requests': {
        'task': 'stake.tasks.stake_finish.finish_stakes',
        'schedule': crontab(hour=21, minute=0),
        'options': {
            'queue': 'celery',
            'expire': 36000
        },
    },

    'free_missing_locks': {
        'task': 'ledger.tasks.locks.free_missing_locks',
        'schedule': 15,
        'options': {
            'queue': 'celery',
            'expire': 15
        },
    },

    'pending_otc_trades': {
        'task': 'ledger.tasks.otc.accept_pending_otc_trades',
        'schedule': 30,
        'options': {
            'queue': 'celery',
            'expire': 30
        },
    },

    'fill_trades_revenue': {
        'task': 'accounting.tasks.revenue.fill_revenue_filled_prices',
        'schedule': 30 * TASK_MULTIPLIER,
        'options': {
            'queue': 'celery',
            'expire': 30 * TASK_MULTIPLIER
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
        'schedule': 60 * TASK_MULTIPLIER,
        'options': {
            'queue': 'finance',
            'expire': 60 * TASK_MULTIPLIER
        },
    },

    'update_accounts_pnl': {
        'task': 'ledger.tasks.pnl.create_pnl_histories',
        'schedule': crontab(hour=20, minute=30),
        'options': {
            'queue': 'history',
        }
    },

    'create_analytics': {
        'task': 'analytics.tasks.create_analytics',
        'schedule': crontab(hour=21, minute=0),
        'options': {
            'queue': 'history',
        }
    },

    'trigger_events': {
        'task': 'analytics.tasks.trigger_kafka_event',
        'schedule': 2,
        'options': {
            'queue': 'history',
            'expire': 5
        }
    },

    'create_snapshot': {
        'task': 'ledger.tasks.snapshot.create_snapshot',
        'schedule': crontab(minute='1-59/5'),
        'options': {
            'queue': 'history',
            'expire': 200
        }
    },
    'provider_income': {
        'task': 'accounting.tasks.provider.fill_provider_incomes',
        'schedule': crontab(minute=30),
        'options': {
            'queue': 'history',
            'expire': 3600,
        },
    },
    'blocklink_incomes': {
        'task': 'accounting.tasks.blocklink.fill_blocklink_incomes',
        'schedule': crontab(minute=30),
        'options': {
            'queue': 'history',
            'expire': 3600,
        },
    },

    'create_vault_snapshot': {
        'task': 'accounting.tasks.vault.update_vaults',
        'schedule': crontab(minute='*/5'),
        'options': {
            'queue': 'vault',
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

    'send_notifications_push': {
        'task': 'accounts.tasks.notification.send_notifications_push',
        'schedule': 5 * TASK_MULTIPLIER,
        'options': {
            'queue': 'notif-manager',
            'expire': 5 * TASK_MULTIPLIER
        },
    },
    'process_bulk_notifications': {
        'task': 'accounts.tasks.notification.process_bulk_notifications',
        'schedule': 60 * TASK_MULTIPLIER,
        'options': {
            'queue': 'notif-manager',
            'expire': 60 * TASK_MULTIPLIER
        },
    },
    'send_sms_notifications': {
        'task': 'accounts.tasks.notification.send_sms_notifications',
        'schedule': 10 * TASK_MULTIPLIER,
        'options': {
            'queue': 'notif-manager',
            'expire': 10 * TASK_MULTIPLIER
        },
    },

    'send_signup_not_deposited_sms': {
        'task': 'retention.tasks.send_signup_not_deposited_sms',
        'schedule': 60,
        'options': {
            'queue': 'celery',
            'expire': 60
        },
    },

    'send_signup_not_verified_push': {
        'task': 'retention.tasks.send_signup_not_verified_push',
        'schedule': 60,
        'options': {
            'queue': 'celery',
            'expire': 60
        },
    },

    'expire_missions': {
        'task': 'gamify.tasks.deactivate_expired_missions',
        'schedule': crontab(hour=20, minute=30),
        'options': {
            'queue': 'celery',
            'expire': 3600
        },
    },
}
