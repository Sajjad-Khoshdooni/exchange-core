# Generated by Django 4.1.3 on 2023-01-18 10:33

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0100_historicaluser_custom_crypto_withdraw_ceil_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaluser',
            name='custom_crypto_withdraw_ceil',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='user',
            name='custom_crypto_withdraw_ceil',
            field=models.PositiveBigIntegerField(blank=True, null=True),
        ),
    ]