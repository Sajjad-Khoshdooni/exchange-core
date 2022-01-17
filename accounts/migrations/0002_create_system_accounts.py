# Generated by Django 4.0 on 2022-01-01 13:05

from django.db import migrations, models, transaction
import django.db.models.deletion


def create_system_accounts(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')

    with transaction.atomic():
        Account.objects.get_or_create(type='s')
        Account.objects.get_or_create(type='o')


def delete_system_accounts(apps, schema_editor):
    Account = apps.get_model('accounts', 'Account')
    Account.objects.exclude(type='').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_system_accounts, delete_system_accounts),
    ]
