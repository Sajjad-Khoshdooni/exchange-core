# Generated by Django 4.0 on 2022-08-30 10:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0118_addresskey_architecture_addresskey_public_address'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='depositaddress',
            name='is_registered',
        ),
    ]
