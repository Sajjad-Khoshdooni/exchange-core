# Generated by Django 4.1.3 on 2023-12-10 11:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('health', '0006_alter_alerttype_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='alerttype',
            name='type',
            field=models.CharField(choices=[('unhandled_crypto_withdraw', 'unhandled_crypto_withdraw'), ('crypto_long_confirmation', 'crypto_long_confirmation'), ('unhandled_fiat_withdraw', 'unhandled_fiat_withdraw'), ('long_pending_fiat_withdraw', 'long_pending_fiat_withdraw'), ('canceled_otc', 'canceled_otc'), ('asset_hedge', 'asset_hedge'), ('total_hedge', 'total_hedge'), ('risky_margin_ratio', 'risky_margin_ratio'), ('vault_low_base_balance', 'vault_low_base_balance'), ('vault_high_balance', 'vault_high_balance'), ('hot_wallet_low_balance', 'hot_wallet_low_balance')], max_length=32),
        ),
    ]
