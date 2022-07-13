# Generated by Django 4.0 on 2022-07-12 14:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0105_alter_trx_scope_alter_wallet_market'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trx',
            name='scope',
            field=models.CharField(choices=[('t', 'trade'), ('f', 'transfer'), ('m', 'margin transfer'), ('b', 'margin borrow'), ('c', 'commission'), ('l', 'liquid'), ('fl', 'fast liquid'), ('p', 'prize'), ('r', 'revert'), ('ad', 'airdrop'), ('st', 'stake'), ('sr', 'stake_revenue')], max_length=2),
        ),
    ]
