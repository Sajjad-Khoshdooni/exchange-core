# Generated by Django 4.1.3 on 2023-07-23 14:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0191_historicaltransfer'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemsnapshot',
            name='verified',
            field=models.BooleanField(default=False),
        ),
    ]
