# Generated by Django 4.0 on 2022-08-21 06:44

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0080_apptrackercode_alter_attribution_gps_adid'),
    ]

    operations = [
        migrations.DeleteModel(
            name='AppTrackerCode',
        ),
    ]
