# Generated by Django 4.0 on 2022-04-17 13:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('market', '0011_order_market_new_orders_price_idx'),
    ]

    operations = [
        migrations.AddField(
            model_name='fillorder',
            name='trade_source',
            field=models.CharField(blank=True, choices=[('otc', 'depth'), (None, 'ordinary')], max_length=8, null=True),
        ),
    ]
