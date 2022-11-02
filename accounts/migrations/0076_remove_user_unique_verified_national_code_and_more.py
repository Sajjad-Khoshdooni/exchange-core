# Generated by Django 4.0 on 2022-08-11 11:11

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0075_historicaluser_national_code_phone_verified_and_more'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='user',
            name='unique_verified_national_code',
        ),
        migrations.RemoveField(
            model_name='historicaluser',
            name='national_code_duplicated_alert',
        ),
        migrations.RemoveField(
            model_name='user',
            name='national_code_duplicated_alert',
        ),
    ]