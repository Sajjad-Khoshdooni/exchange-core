# Generated by Django 4.0 on 2022-02-06 13:35
import json

from django.db import migrations

from provider.exchanges import BinanceSpotHandler


def create_network_assets(apps, schema_editor):
    Asset = apps.get_model('ledger', 'Asset')
    Network = apps.get_model('ledger', 'Network')
    NetworkAsset = apps.get_model('ledger', 'NetworkAsset')

    assets = Asset.objects.all()
    assets_map = {a.symbol: a for a in assets}

    coins = BinanceSpotHandler.get_all_coins()

    for c in coins:
        if c['coin'] not in assets_map:
            continue

        asset = assets_map[c['coin']]

        for n in c['networkList']:
            network, _ = Network.objects.get_or_create(symbol=n['network'], defaults={
                'name': n['name'],
                'can_withdraw': False,
                'can_deposit': False,
                'address_regex': n['addressRegex'],
                'min_confirm': n['minConfirm'],
                'unlock_confirm': n['unLockConfirm'],
            })

            NetworkAsset.objects.get_or_create(
                asset=asset,
                network=network,
                defaults={
                    'withdraw_fee': n['withdrawFee'],
                    'withdraw_min': n['withdrawMin'],
                    'withdraw_max': n['withdrawMax'],
                }
            )


class Migration(migrations.Migration):

    dependencies = [
        ('ledger', '0041_rename_withdraw_commission_networkasset_withdraw_fee_and_more'),
    ]

    operations = [
        migrations.RunPython(create_network_assets, migrations.RunPython.noop),
    ]
