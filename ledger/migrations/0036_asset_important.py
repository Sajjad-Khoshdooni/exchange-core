# Generated by Django 4.0 on 2022-02-05 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0035_asset_precision'),
    ]

    operations = [
        migrations.AddField(
            model_name='asset',
            name='important',
            field=models.BooleanField(default=False),
        ),
    ]