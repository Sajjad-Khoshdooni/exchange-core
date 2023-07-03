# Generated by Django 4.1.3 on 2023-07-03 08:58
from django.conf import settings
from django.db import migrations, models


def fill_fake_value_bool(apps, schema_editor):
    TradeRevenue = apps.get_model("accounting", "TradeRevenue")
    TradeRevenue.objects.filter(
        account_id__in=(settings.OTC_ACCOUNT_ID, settings.MARKET_MAKER_ACCOUNT_ID, settings.TRADER_ACCOUNT_ID)
    ).update(value_is_fake=True)


class Migration(migrations.Migration):

    dependencies = [
        ('accounting', '0024_auto_20230702_1733'),
    ]

    operations = [
        migrations.AddField(
            model_name='traderevenue',
            name='value_is_fake',
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(fill_fake_value_bool),
    ]
