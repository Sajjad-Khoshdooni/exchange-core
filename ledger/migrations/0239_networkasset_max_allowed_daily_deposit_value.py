# Generated by Django 4.1.3 on 2024-02-08 15:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0238_alter_depositrecoveryrequest_status_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='networkasset',
            name='max_allowed_daily_deposit_value',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]