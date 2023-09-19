# Generated by Django 4.1.3 on 2023-09-18 12:29

from django.db import migrations


def populate_wallet_balances(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    AssetAlert = apps.get_model('ledger', 'AssetAlert')
    BulkAssetAlert = apps.get_model('ledger', 'BulkAssetAlert')

    user_ids = set(
        AssetAlert.objects.values_list('user', flat=True).distinct()
    ) | set(
        BulkAssetAlert.objects.values_list('user', flat=True).distinct()
    )

    User.objects.filter(id__in=user_ids).update(is_price_notif_on=True)


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0216_merge_20230911_1209'),
    ]

    operations = [
        migrations.RunPython(code=populate_wallet_balances, reverse_code=migrations.RunPython.noop)
    ]