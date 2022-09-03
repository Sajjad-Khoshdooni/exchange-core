# Generated by Django 4.0 on 2022-08-30 10:01

from django.db import migrations, models
from django.db.models import F


def populate_architecture(apps, sch):
    AddressKey = apps.get_model('ledger', 'AddressKey')
    AddressKey.objects.all().update(architecture='ETH')


def populate_public_address(apps, sch):
    AddressKey = apps.get_model('ledger', 'AddressKey')
    AddressKey.objects.all().update(public_address=F('address'))


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0117_alter_transfer_source'),
    ]

    operations = [
        migrations.AddField(
            model_name='addresskey',
            name='architecture',
            field=models.CharField(null=True, max_length=16),
            preserve_default=False,
        ),
        migrations.RunPython(populate_architecture, reverse_code=migrations.RunPython.noop),

        migrations.AlterField(
            model_name='addresskey',
            name='architecture',
            field=models.CharField(max_length=16),
            preserve_default=False,
        ),

        migrations.AddField(
            model_name='addresskey',
            name='public_address',
            field=models.CharField(null=True, max_length=256),
            preserve_default=False,
        ),
        migrations.RunPython(populate_public_address, reverse_code=migrations.RunPython.noop),
    ]
