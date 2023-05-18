# Generated by Django 4.1.3 on 2023-05-10 08:38
from datetime import timedelta

from django.db import migrations, models
from django.db.models import F


def populate_prizes(apps, schema_editor):
    Prize = apps.get_model('ledger', 'Prize')

    Prize.objects.filter(achievement__voucher=True).update(voucher_expiration=F('created') + timedelta(days=30))


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0177_addresskey_ledger_addresskey_unique_account_architecture'),
    ]

    operations = [
        migrations.AddField(
            model_name='prize',
            name='voucher_expiration',
            field=models.DateTimeField(blank=True, null=True),
        ),

        migrations.RunPython(
            code=populate_prizes,
            reverse_code=migrations.RunPython.noop
        )
    ]