from uuid import uuid4

from accounts.models import Account, Notification
from ledger.models import Asset, Wallet, Trx
from ledger.utils.external_price import get_external_price, BUY
from ledger.utils.otc import get_otc_spread, spread_to_multiplier
from ledger.utils.precision import humanize_number
from ledger.utils.wallet_pipeline import WalletPipeline


def sell_all_assets_to_irt(asset: Asset):
    assert asset.otc_status != Asset.ACTIVE
    assert asset.symbol != Asset.IRT

    irt = Asset.get(Asset.IRT)

    group_id = uuid4()

    system_coin = asset.get_wallet(Account.system())
    system_irt = irt.get_wallet(Account.system())

    price = get_external_price(
        coin=asset.symbol,
        base_coin=Asset.IRT,
        side=BUY,
    )

    spread = get_otc_spread(
        coin=asset.symbol,
        base_coin=Asset.IRT,
        side=BUY
    )

    price = price * spread_to_multiplier(spread, BUY)

    wallets = Wallet.objects.filter(asset=asset, balance__gt=0, market=Wallet.SPOT, account__type=Account.ORDINARY)

    with WalletPipeline() as pipeline:
        for wallet in wallets:
            amount = wallet.balance
            irt_amount = amount * price

            pipeline.new_trx(
                sender=wallet,
                receiver=system_coin,
                amount=amount,
                group_id=group_id,
                scope=Trx.DELIST
            )
            pipeline.new_trx(
                sender=system_irt,
                receiver=irt.get_wallet(wallet.account),
                amount=irt_amount,
                group_id=group_id,
                scope=Trx.DELIST
            )

            if irt_amount >= 1:
                Notification.send(
                    recipient=wallet.account.user,
                    title='تبدیل خودکار توکن {}'.format(asset.symbol),
                    message='با توجه به اطلاع‌رسانی‌های مکرر قبلی مبنی بر حذف توکن {}، مقدار {} {} به {} تومان تبدیل شد.'.format(
                        asset.symbol, humanize_number(amount), asset.name_fa,
                        humanize_number(int(irt_amount))
                    ),
                    level=Notification.INFO,
                )
