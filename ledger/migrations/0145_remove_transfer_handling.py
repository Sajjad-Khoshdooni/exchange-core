# Generated by Django 4.1.3 on 2022-12-12 07:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0144_alter_transfer_source'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transfer',
            name='handling',
        ),
    ]