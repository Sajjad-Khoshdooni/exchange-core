# Generated by Django 4.0 on 2022-05-22 11:15

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0083_asset_has_description'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='has_description',
        ),
    ]
