# Generated by Django 4.0 on 2022-08-22 07:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0081_delete_apptrackercode'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attribution',
            name='user_agent',
            field=models.CharField(blank=True, max_length=512),
        ),
    ]
