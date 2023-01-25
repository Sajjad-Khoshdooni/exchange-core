import logging
from datetime import datetime
from decimal import Decimal

from accounting.models import Vault
from accounting.models.vault import VaultData
from financial.utils.stats import get_total_fiat_irt
from ledger.models import Asset
from ledger.utils.overview import get_internal_asset_deposits
from ledger.utils.price import get_prices_dict, BUY
from ledger.utils.provider import get_provider_requester

logger = logging.getLogger(__name__)


def update_provider_vaults(now: datetime, usdt_irt: Decimal):
    logger.info('updating provider vaults')
    provider = get_provider_requester()

    profiles = provider.get_profiles()

    for profile in profiles:
        profile_id = profile['id']

        logger.info('updating provider profile = %d' % profile_id)

        for market in Vault.MARKETS:
            vault, _ = Vault.objects.get_or_create(
                type=Vault.PROVIDER,
                market=market,
                key=profile_id,

                defaults={
                    'name': '%s-%s' % (profile['exchange'], profile['scope'])
                }
            )

            vault_data = []

            balances_data = provider.get_balances(profile, market)
            prices = get_prices_dict(coins=list(balances_data.keys()), side=BUY)

            if not balances_data:
                continue

            for coin, balance in balances_data.items():
                balance = Decimal(balance)
                value = balance * prices.get(coin, 0)

                vault_data.append(
                    VaultData(
                        coin=coin,
                        balance=balance,
                        value_usdt=value,
                        value_irt=value * usdt_irt,
                    )
                )

            vault.update_vault_all_items(now, vault_data)


def update_hot_wallet_vault(now: datetime, usdt_irt: Decimal):
    logger.info('updating hotwallet vaults')

    data = get_internal_asset_deposits()
    prices = get_prices_dict(coins=list(data.keys()), side=BUY)

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

    amount = get_total_fiat_irt()

    vault_data = [
        VaultData(
            coin=Asset.IRT,
            balance=amount,
            value_usdt=amount / usdt_irt,
            value_irt=amount
        )
    ]

    vault.update_vault_all_items(now, vault_data)


def update_cold_wallet_vaults(now: datetime, usdt_irt: Decimal):
    logger.info('updating cold wallet vaults')
