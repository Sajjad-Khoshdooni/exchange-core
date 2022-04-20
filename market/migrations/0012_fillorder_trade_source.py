# Generated by Django 4.0 on 2022-04-18 13:31

from django.db import migrations, models


def set_source_trade(apps, schema_editor):
    FillOrder = apps.get_model('market', 'FillOrder')
    FillOrder.objects.filter(
        maker_order__wallet__account__type='s',
        taker_order__wallet__account__type='s',
    ).update(trade_source='system')


class Migration(migrations.Migration):
    dependencies = [
        ('market', '0011_order_market_new_orders_price_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='fillorder',
            name='trade_source',
            field=models.CharField(blank=True, choices=[('otc', 'otc'), (None, 'market'), ('system', 'system')], db_index=True, max_length=8, null=True),
        ),
        migrations.RunPython(
            code=set_source_trade, reverse_code=migrations.RunPython.noop
        ),
    ]
