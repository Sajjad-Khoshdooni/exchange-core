# Generated by Django 4.1.3 on 2023-09-02 10:39

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0214_networkasset_last_provider_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='alerttrigger',
            name='chanel',
            field=models.IntegerField(default=None),
        ),
        migrations.AddField(
            model_name='alerttrigger',
            name='is_chanel_changed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='asset',
            name='price_alert_chanel_sensitivity',
            field=models.DecimalField(blank=True, decimal_places=8, max_digits=30, null=True, validators=[django.core.validators.MinValueValidator(0)]),
        ),
        migrations.AlterField(
            model_name='alerttrigger',
            name='interval',
            field=models.CharField(choices=[('5m', 'پنج\u200c دقیقه'), ('1h', '\u200cیک\u200c ساعت'), ('3h', 'سه ساعت'), ('6h', 'شش ساعت'), ('12h', 'دوازده ساعت'), ('24h', 'یک روز')], max_length=15),
        ),
        migrations.AddIndex(
            model_name='alerttrigger',
            index=models.Index(fields=['asset', 'is_chanel_changed', 'is_triggered'], name='chanel_change_alert_idx'),
        ),
        migrations.AddIndex(
            model_name='alerttrigger',
            index=models.Index(fields=['asset', 'is_triggered', 'interval', 'created'], name='ledger_aler_asset_i_2e8e17_idx'),
        ),
    ]
