# Generated by Django 4.0 on 2022-04-09 07:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_sentsms'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='SentSMS',
            new_name='ExternalNotification',
        ),
    ]
