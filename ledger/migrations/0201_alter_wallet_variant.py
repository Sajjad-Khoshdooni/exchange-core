# Generated by Django 4.1.3 on 2023-08-07 09:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0200_alter_asset_spread_category_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='wallet',
            name='variant',
            field=models.UUIDField(blank=True, default=None, null=True),
        ),
    ]