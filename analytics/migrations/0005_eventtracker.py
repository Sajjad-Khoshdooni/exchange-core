# Generated by Django 4.1.3 on 2023-06-10 07:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0004_activetrader_delete_dailyanalytics'),
    ]

    operations = [
        migrations.CreateModel(
            name='EventTracker',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateField(auto_now_add=True)),
                ('updated', models.DateField(auto_now=True)),
                ('name', models.CharField(max_length=30)),
                ('last_trade_id', models.IntegerField(default=0)),
                ('last_otc_trade_id', models.IntegerField(default=0)),
                ('last_transfer_id', models.IntegerField(default=0)),
                ('last_fiat_withdraw_id', models.IntegerField(default=0)),
                ('last_payment_id', models.IntegerField(default=0)),
                ('last_user_id', models.IntegerField(default=0)),
                ('last_login_id', models.IntegerField(default=0)),
                ('last_prize_id', models.IntegerField(default=0)),
                ('last_staking_id', models.IntegerField(default=0)),
                ('last_traffic_source_id', models.IntegerField(default=0)),
            ],
        ),
    ]
