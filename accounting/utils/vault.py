import logging
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from accounting.models import Vault, Account
from accounting.models.vault import VaultData, AssetPrice, VaultItem, ReservedAsset
from financial.models import Gateway
from financial.utils.withdraw import FiatWithdraw
from ledger.models import Asset
from ledger.utils.overview import get_internal_asset_deposits
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger(__name__)


def update_provider_vaults(now: datetime, prices: dict):
    logger.info('updating provider vaults')
    provider = get_provider_requester()

    profiles = provider.get_profiles()

    for profile in profiles:
        profile_id = profile['id']

        logger.info('updating provider profile = %d' % profile_id)

        exchange = profile['exchange']

        if exchange == 'binance':
            markets = Vault.MARKETS
        else:
            markets = [Vault.SPOT]

        for market in markets:
            vault, _ = Vault.objects.get_or_create(
                type=Vault.PROVIDER,
                market=market,
                key=profile_id,

                defaults={
                    'name': '%s-%s' % (exchange, profile['id'])
                }
            )

            vault_data = []

            balances_data = provider.get_balances(profile_id, market)

            if not balances_data:
                continue

            balances = balances_data['balances']
            real_value = balances_data['real_value'] and Decimal(balances_data['real_value'])

            if not balances:
                continue

            for coin, balance in balances.items():
                balance = Decimal(balance)
                price = prices.get(coin, 0)

                value = balance * price

                vault_data.append(
                    VaultData(
                        coin=coin,
                        balance=balance,
                        value_usdt=value,
                        value_irt=value / prices['IRT']
                    )
                )

            vault.update_vault_all_items(now, vault_data, real_vault_value=real_value)


def update_hot_wallet_vault(now: datetime, prices: dict):
    logger.info('updating hotwallet vaults')

    data = get_internal_asset_deposits()

    vault, _ = Vault.objects.get_or_create(
        type=Vault.HOT_WALLET,
        market=Vault.SPOT,
        key='main',

        defaults={
            'name': 'main'
        }
    )

    vault_data = []

    for coin, amount in data.items():
        value = amount * prices.get(coin, 0)

        vault_data.append(
            VaultData(
                coin=coin,
                balance=amount,
                value_usdt=value,
                value_irt=value / prices['IRT']
            )
        )

    vault.update_vault_all_items(now, vault_data)


def update_gateway_vaults(now: datetime, prices: dict):
    logger.info('updating gateway vaults')

    for gateway in Gateway.objects.exclude(withdraw_api_secret_encrypted=''):
        vault, _ = Vault.objects.get_or_create(
            type=Vault.GATEWAY,
            market=Vault.SPOT,
            key=gateway.id,
            defaults={
                'name': str(gateway)
            }
        )

        try:
            handler = FiatWithdraw.get_withdraw_channel(gateway)
            amount = handler.get_total_wallet_irt_value()

            vault.update_vault_all_items(now, [
                VaultData(
                    coin=Asset.IRT,
                    balance=amount,
                    value_usdt=amount * prices['IRT'],
                    value_irt=amount
                )
            ])
        except:
            pass


def update_cold_wallet_vaults(now: datetime, prices: dict):
    logger.info('updating cold & manual wallet vaults')

    for vault_item in VaultItem.objects.filter(vault__type__in=(Vault.COLD_WALLET, Vault.MANUAL)):
        price = prices.get(vault_item.coin, 0)
        vault_item.value_usdt = vault_item.balance * price
        vault_item.value_irt = vault_item.value_usdt / prices['IRT']
        vault_item.save(update_fields=['value_usdt', 'value_irt'])

    for vault in Vault.objects.filter(type__in=(Vault.COLD_WALLET, Vault.MANUAL)):
        vault.update_real_value(now)


def update_bank_vaults(now: datetime, prices: dict):
    for account in Account.objects.filter(create_vault=True):
        vault, _ = Vault.objects.update_or_create(
            type=Vault.BANK,
            market=Vault.SPOT,
            key=account.id,

            defaults={
                'name': account.name
            }
        )

        amount = account.get_balance()

        vault.update_vault_all_items(now, [
            VaultData(
                coin=Asset.IRT,
                balance=amount,
                value_usdt=amount * prices['IRT'],
                value_irt=amount
            )
        ])


def update_reserved_assets_value(now: datetime, prices: dict):
    for res in ReservedAsset.objects.all():
        res.value_usdt = res.amount * prices.get(res.coin, 0)
        res.value_irt = res.value_usdt / prices['IRT']
        res.save(update_fields=['value_usdt', 'value_irt'])


def update_asset_prices(now: datetime, prices: dict):
    logger.info('updating asset prices')

    existing_assets = AssetPrice.objects.filter(coin__in=prices)
    existing_coins = set(existing_assets.values_list('coin', flat=True))

    now = timezone.now()

    missing_assets = []
    for coin in set(prices) - existing_coins:
        missing_assets.append(
            AssetPrice(
                updated=now,
                coin=coin,
                price=prices.get(coin)
            )
        )

    AssetPrice.objects.bulk_create(missing_assets)

    for asset in existing_assets:
        asset.price = prices.get(asset.coin)
        asset.updated = now

    AssetPrice.objects.bulk_update(existing_assets, ['price', 'updated'])
