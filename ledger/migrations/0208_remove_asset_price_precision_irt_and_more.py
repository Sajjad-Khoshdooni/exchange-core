# Generated by Django 4.1.3 on 2023-08-20 10:38

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0207_alter_historicaltransfer_created_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='price_precision_irt',
        ),
        migrations.RemoveField(
            model_name='asset',
            name='price_precision_usdt',
        ),
    ]
