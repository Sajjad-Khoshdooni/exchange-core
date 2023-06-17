# Generated by Django 4.1.3 on 2023-06-15 12:14

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('financial', '0087_gateway_max_daily_deposit_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentidrequest',
            name='deposit_time',
            field=models.DateTimeField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
