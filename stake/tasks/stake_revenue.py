from celery import shared_task
from django.db import transaction

from accounts.models import Account
from ledger.models import Trx, Wallet
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeRequest, StakeRevenue


@shared_task(queue='celery')
def create_stake_revenue():
    stake_requests = StakeRequest.objects.filter(status=StakeRequest.DONE)
    system = Account.system()
    for stake_request in stake_requests:
        asset = stake_request.stake_option.asset
        revenue = stake_request.amount * stake_request.stake_option.apr / 100 / 365

        try:
            with WalletPipeline() as pipeline:
                stake_revenue = StakeRevenue.objects.create(
                    stake_request=stake_request,
                    revenue=revenue
                )
                pipeline.new_trx(
                    group_id=stake_revenue.group_id,
                    sender=asset.get_wallet(system, Wallet.STAKE),
                    receiver=asset.get_wallet(stake_request.account, Wallet.STAKE),
                    amount=revenue,
                    scope=Trx.STAKE_REVENUE
                )

        except:
            print('duplicate stake_revenue')
