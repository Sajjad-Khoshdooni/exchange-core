import logging
from datetime import datetime
from decimal import Decimal

from django.utils import timezone

from accounting.models import Vault
from accounting.models.vault import VaultData, AssetPrice, VaultItem, ReservedAsset
from financial.utils.stats import get_total_fiat_irt
from ledger.models import Asset
from ledger.utils.external_price import get_external_usdt_prices, get_external_price, BUY
from ledger.utils.overview import get_internal_asset_deposits
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger(__name__)


def update_provider_vaults(now: datetime, usdt_irt: Decimal):
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
                    'name': '%s-%s' % (exchange, profile['scope'])
                }
            )

            vault_data = []

            balances_data = provider.get_balances(profile_id, market)

            if not balances_data:
                continue

            balances = balances_data['balances']
            real_value = balances_data['real_value'] and Decimal(balances_data['real_value'])

            prices = get_external_usdt_prices(
                coins=list(balances.keys()),
                side=BUY,
                allow_stale=True,
            )

            for coin, balance in balances.items():
                balance = Decimal(balance)
                price = prices.get(coin, 0)

                if coin == Asset.IRT:
                    price = get_external_price(Asset.IRT, base_coin=Asset.USDT, side=BUY)

                value = balance * price

                vault_data.append(
                    VaultData(
                        coin=coin,
                        balance=balance,
                        value_usdt=value,
                        value_irt=value * usdt_irt,
                    )
                )

            vault.update_vault_all_items(now, vault_data, real_vault_value=real_value)


def update_hot_wallet_vault(now: datetime, usdt_irt: Decimal):
    logger.info('updating hotwallet vaults')

    data = get_internal_asset_deposits()
    prices = get_external_usdt_prices(
        coins=list(data.keys()),
        side=BUY,
        allow_stale=True
    )

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
                value_irt=value * usdt_irt
            )
        )

    vault.update_vault_all_items(now, vault_data)


def update_gateway_vaults(now: datetime, usdt_irt: Decimal):
    logger.info('updating gateway vaults')

    vault, _ = Vault.objects.get_or_create(
        type=Vault.GATEWAY,
        market=Vault.SPOT,
        key='main',
        defaults={
            'name': 'main'
        }
    )

    try:
        amount = get_total_fiat_irt(strict=True)

        vault_data = [
            VaultData(
                coin=Asset.IRT,
                balance=amount,
                value_usdt=amount / usdt_irt,
                value_irt=amount
            )
        ]

        vault.update_vault_all_items(now, vault_data)
    except:
        pass


def update_cold_wallet_vaults(usdt_irt: Decimal):
    logger.info('updating cold & manual wallet vaults')

    for vault_item in VaultItem.objects.filter(vault__type__in=(Vault.COLD_WALLET, Vault.MANUAL)):
        price = get_external_price(vault_item.coin, base_coin=Asset.USDT, side=BUY, allow_stale=True) or 0
        vault_item.value_usdt = vault_item.balance * price
        vault_item.value_irt = vault_item.value_usdt * usdt_irt
        vault_item.save(update_fields=['value_usdt', 'value_irt'])

    for vault in Vault.objects.filter(type__in=(Vault.COLD_WALLET, Vault.MANUAL)):
        vault.update_real_value()


def update_reserved_assets_value(usdt_irt):
    coins = list(ReservedAsset.objects.values_list('coin', flat=True))
    prices = get_external_usdt_prices(coins=coins, side=BUY, allow_stale=True)

    for res in ReservedAsset.objects.all():
        res.value_usdt = res.amount * prices.get(res.coin, 0)
        res.value_irt = res.value_usdt * usdt_irt
        res.save(update_fields=['value_usdt', 'value_irt'])


def update_asset_prices():
    logger.info('updating asset prices')

    prices = get_external_usdt_prices(
        coins=list(Asset.live_objects.values_list('symbol', flat=True)),
        side=BUY,
        allow_stale=True,
        set_bulk_cache=True
    )

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
