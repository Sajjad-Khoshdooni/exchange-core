# Generated by Django 4.0 on 2022-08-31 06:12

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0131_systemsnapshot_kucoin_spot_systemsnapshot_mexc_spot'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='original_name_fa',
            field=models.CharField(blank=True, max_length=32),
        ),
    ]
