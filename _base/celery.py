import os

from celery import Celery
# Set the default Django settings module for the 'celery' program.
from celery.schedules import crontab
from django.conf import settings

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
    'coin_market_cap_update': {
        'task': 'collector.tasks.coin_market_cap.update_coin_market_cap',
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
    'update_provider_withdraw': {
        'task': 'ledger.tasks.withdraw.update_provider_withdraw',
        'schedule': 10,
        'options': {
            'queue': 'binance',
            'expire': 10
        },
    },

    'update_withdraws': {
        'task': 'ledger.tasks.withdraw.update_withdraws',
        'schedule': 10,
        'options': {
            'queue': 'blocklink',
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
    'create_transfer_history': {
        'task': 'provider.tasks.binance.create_transfer_history',
        'schedule': 1800,
        'options': {
            'queue': 'binance',
            'expire': 1800,
        }
    },
    'get_binance_wallet': {
        'task': 'provider.tasks.binance.get_binance_wallet',
        'schedule': 900,
        'options': {
            'queue': 'binance',
            'expire': 900,
        }
    },
    # market tasks
    'create depth orders': {
        'task': 'market.tasks.market_maker.create_depth_orders',
        'schedule': 30,
        'options': {
            'queue': 'market',
            'expire': 30
        },
    },
    'update maker orders': {
        'task': 'market.tasks.market_maker.update_maker_orders',
        'schedule': 10,
        'options': {
            'queue': 'market',
            'expire': 10
        },
    },
    'handle open stop loss': {
        'task': 'market.tasks.stop_loss.handle_stop_loss',
        'schedule': 1,
        'options': {
            'queue': 'stop_loss',
            'expire': 1
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
    'create_stake_revenue': {
        'task': 'stake.tasks.stake_revenue.create_stake_revenue',
        'schedule': crontab(hour=19, minute=30),
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

    'check_margin_level': {
        'task': 'ledger.tasks.margin.check_margin_level',
        'schedule': 5,
        'options': {
            'queue': 'margin',
            'expire': 5
        },
    },

    'retention_leads_to_signup': {
        'task': 'accounts.tasks.retention.retention_leads_to_signup',
        'schedule': 3600,
        'options': {
            'queue': 'retention',
            'expire': 3600
        },
    },

    'retention_actions': {
        'task': 'accounts.tasks.retention.retention_actions',
        'schedule': 3600,
        'options': {
            'queue': 'retention',
            'expire': 3600
        },
    },

    'update_withdraw_status': {
        'task': 'financial.tasks.withdraw.update_withdraw_status',
        'schedule': 300,
        'options': {
            'queue': 'finance',
            'expire': 300
        },
    },

    'handle_missing_payments': {
        'task': 'financial.tasks.gateway.handle_missing_payments',
        'schedule': 300,
        'options': {
            'queue': 'finance',
            'expire': 60
        },
    },

    'random_trader': {
        'task': 'trader.tasks.random_trader.random_trader',
        'schedule': 17,
        'options': {
            'queue': 'trader-ma',
            'expire': 17
        }
    },
    'carrot_trader': {
        'task': 'trader.tasks.carrot_trader.carrot_trader',
        'schedule': 7,
        'options': {
            'queue': 'trader-ma',
            'expire': 7
        }
    },

    'health_alert_pending': {
        'task': 'health.tasks.alert_pending.alert_pending',
        'schedule': 600,
        'options': {
            'queue': 'celery',
            'expire': 3600
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
    'create_accounting_report': {
        'task': 'accounting.tasks.weekly_fiat_transfer.create_weekly_accounting_report',
        'schedule': crontab(hour=19, minute=30, day_of_week=7),
        'options': {
            'queue': 'accounting',
            'expire': 36000
        },
    },
}

if settings.DEBUG_OR_TESTING:
    app.conf.beat_schedule = {
        'coin_market_cap_update': {
            'task': 'collector.tasks.coin_market_cap.update_coin_market_cap',
            # 'schedule': crontab(minute=0, hour=2),
            'schedule': crontab(minute="*/30"),
        },
        # market tasks
        'create depth orders': {
            'task': 'market.tasks.market_maker.create_depth_orders',
            'schedule': 5,
            'options': {
                'queue': 'market',
                'expire': 5
            },
        },
        'update maker orders': {
            'task': 'market.tasks.market_maker.update_maker_orders',
            'schedule': 1,
            'options': {
                'queue': 'market',
                'expire': 2
            },
        },
        # 'moving_average_trader': {
        #     'task': 'trader.tasks.moving_average.update_all_moving_averages',
        #     'schedule': 67,
        #     'options': {
        #         'queue': 'trader-ma',
        #         'expire': 67
        #     }
        # },
        'handle open stop loss': {
            'task': 'market.tasks.stop_loss.handle_stop_loss',
            'schedule': 1,
            'options': {
                'queue': 'stop_loss',
                'expire': 1
            },
        },
        'check_margin_level': {
            'task': 'ledger.tasks.margin.check_margin_level',
            'schedule': 5,
            'options': {
                'queue': 'margin',
                'expire': 5
            },
        },

        'random_trader': {
            'task': 'trader.tasks.random_trader.random_trader',
            'schedule': 17,
            'options': {
                'queue': 'trader-ma',
                'expire': 17
            }
        },
        'carrot_trader': {
            'task': 'trader.tasks.carrot_trader.carrot_trader',
            'schedule': 7,
            'options': {
                'queue': 'trader-ma',
                'expire': 7
            }
        },
        'update_accounts_pnl': {
            'task': 'ledger.tasks.pnl.create_pnl_histories',
            'schedule': crontab(hour=20, minute=30),
            'options': {
                'queue': 'celery',
            }
        },
    }
