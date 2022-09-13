# Generated by Django 4.0 on 2022-08-28 13:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0129_merge_20220828_1814'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='hedge_method',
            field=models.CharField(blank=True, choices=[('kucoin-spot', 'kucoin-spot'), ('kucoin-future', 'kucoin-future'), ('binance-spot', 'binance-spot'), ('binance-future', 'binance-future'), ('mexc-spot', 'mexc-spot'), ('mexc-future', 'mexc-future'), ('', '')], default='binance-future', max_length=32),
        ),
    ]
