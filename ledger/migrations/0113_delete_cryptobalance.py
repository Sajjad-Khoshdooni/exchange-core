# Generated by Django 4.0 on 2022-08-01 12:33

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0112_alter_wallet_unique_together'),
    ]

    operations = [
        migrations.DeleteModel(
            name='CryptoBalance',
        ),
    ]