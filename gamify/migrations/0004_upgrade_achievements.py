# Generated by Django 4.0 on 2022-10-04 13:33

from django.db import migrations
from yekta_config.config import config

from accounts.models import Notification


def upgrade_achievement(apps, schema_editor):
    Mission = apps.get_model('gamify', 'Mission')
    MissionJourney = apps.get_model('gamify', 'MissionJourney')
    Task = apps.get_model('gamify', 'Task')
    Achievement = apps.get_model('gamify', 'Achievement')
    Asset = apps.get_model('ledger', 'Asset')

    journey = MissionJourney.objects.get(name='default')

    mission = Mission.objects.create(journey=journey, name='referral', order=3, active=False)
    Task.objects.create(
        mission=mission,
        scope='referral',
        title='دعوت از دوستان',
        max=10,
        link='/account/referral',
        description='دوستان خود را به {} دعوت کنید.'.format(config('BRAND')),
        level=Notification.INFO,
    )

    shib = Asset.objects.get(symbol='SHIB')
    Achievement.objects.create(
        mission=mission,
        scope='referral_trade_2m',
        amount=50000,
        asset=shib
    )

    Achievement.objects.update(asset=shib)

    amounts_map = {
        'level2_verify': 30_000,
        'trade_2m': 30_000,
        'trade_s2': 100_000,
        'referral_trade_2m': 50_000
    }

    achievements = Achievement.objects.all()

    for a in achievements:
        a.amount = amounts_map[a.scope]

    Achievement.objects.bulk_update(achievements, ['amount'])


class Migration(migrations.Migration):

    dependencies = [
        ('gamify', '0003_remove_achievement_scope_achievement_amount_and_more'),
    ]

    operations = [
        migrations.RunPython(
            code=upgrade_achievement, reverse_code=migrations.RunPython.noop
        ),
    ]
