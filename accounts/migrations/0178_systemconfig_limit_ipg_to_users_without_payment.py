# Generated by Django 4.1.3 on 2024-01-20 12:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0177_systemconfig_open_pay_id_to_all'),
    ]

    operations = [
        migrations.AddField(
            model_name='systemconfig',
            name='limit_ipg_to_users_without_payment',
            field=models.BooleanField(default=False),
        ),
    ]