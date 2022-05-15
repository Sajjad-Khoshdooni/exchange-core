# Generated by Django 4.0 on 2022-05-15 12:43

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0050_alter_customtoken_ip_list'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customtoken',
            name='ip_list',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.GenericIPAddressField(default='127.0.0.1'), default=list, size=None),
        ),
    ]
