# Generated by Django 4.0 on 2022-01-30 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0029_alter_accountsecret_account'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='asset',
            name='explorer_link',
        ),
        migrations.AddField(
            model_name='network',
            name='explorer_link',
            field=models.CharField(blank=True, max_length=128),
        ),

        migrations.AlterModelOptions(
            name='asset',
            options={'ordering': ('order',)},
        ),
        migrations.AddField(
            model_name='asset',
            name='enable',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='asset',
            name='order',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='asset',
            name='price_precision_irt',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='asset',
            name='price_precision_usdt',
            field=models.SmallIntegerField(default=2),
        ),
        migrations.AlterField(
            model_name='asset',
            name='max_trade_quantity',
            field=models.DecimalField(decimal_places=2, default=1000000000.0, max_digits=18),
        ),

    ]
