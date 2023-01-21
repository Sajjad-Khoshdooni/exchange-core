# Generated by Django 4.0 on 2022-05-09 15:33

from django.db import migrations, models
from django.db.models import Sum


def populate_trade_volume_irt(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    Prize = apps.get_model('ledger', 'Prize')
    Asset = apps.get_model('ledger', 'Asset')

    asset = Asset.objects.get(symbol='SHIB')

    maker_values = {}
    taker_values = {}

    accounts = Account.objects.filter(id__in=set(maker_values) | set(taker_values))
    for account in accounts:
        account.trade_volume_irt = maker_values.get(account.id, 0) + taker_values.get(account.id, 0)
        account.save(update_fields=['trade_volume_irt'])
        account.refresh_from_db()

    for account in Account.objects.filter(trade_volume_irt__gte=2_000_000):
        Prize.objects.get_or_create(account=account, scope='trade_2m', defaults={'amount': 0, 'asset': asset, 'fake': True})


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0044_merge_20220502_1155'),
        ('market', '0017_alter_order_lock'),
        ('ledger', '0079_prize_fake'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='trade_volume_irt',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.RunPython(
            code=populate_trade_volume_irt,
            reverse_code=migrations.RunPython.noop
        )
    ]
