# Generated by Django 4.1.3 on 2024-01-08 06:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0233_alter_marginleverage_account'),
    ]

    operations = [
        migrations.AlterField(
            model_name='marginhistorymodel',
            name='type',
            field=models.CharField(choices=[('pnl', 'pnl'), ('transfer', 'transfer'), ('trade_fee', 'trade_fee'), ('int_fee', 'int_fee'), ('ins_fee', 'ins_fee'), ('p_transfer', 'p_transfer'), ('dust', 'dust')], max_length=12),
        ),
    ]