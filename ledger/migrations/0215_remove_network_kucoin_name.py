# Generated by Django 4.1.3 on 2023-09-03 05:57

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0214_networkasset_last_provider_update'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='network',
            name='kucoin_name',
        ),
    ]