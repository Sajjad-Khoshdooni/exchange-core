# Generated by Django 4.1.3 on 2023-08-06 08:06

from django.db import migrations, models


def set_existing_as_hedged(apps, schema_editor):
    OTCTrade = apps.get_model('ledger', 'OTCTrade')
    OTCTrade.objects.update(hedged=True)


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0198_alter_coincategory_coins'),
    ]

    operations = [
        migrations.AddField(
            model_name='otctrade',
            name='hedged',
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name='otctrade',
            name='to_buy_amount',
            field=models.DecimalField(decimal_places=8, default=0, max_digits=30),
        ),
        migrations.RunPython(set_existing_as_hedged, migrations.RunPython.noop),
    ]
