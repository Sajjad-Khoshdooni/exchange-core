from celery import shared_task
from django.db import transaction

from accounts.models import Account
from ledger.models import Transfer, Trx
from ledger.utils.wallet_pipeline import WalletPipeline
from stake.models import StakeRequest, StakeRevenue


@shared_task(queue='celery')
def create_stake_revenue():
    stake_requests = StakeRequest.objects.filter(status=StakeRequest.DONE)
    system = Account.stake()
    for stake_request in stake_requests:
        asset = stake_request.stake_option.asset
        revenue = stake_request.amount * stake_request.stake_option._yield

        with transaction.atomic():
            try:
                stake_revenue = StakeRevenue.objects.create(
                    stake_request=stake_request,
                    revenue=revenue
                )

                with WalletPipeline() as pipeline:
                    pipeline.new_trx(
                        group_id=stake_revenue.group_id,
                        sender=asset.get_wallet(system),
                        receiver=asset.get_wallet(stake_request.account),
                        amount=revenue,
                        scope=Trx.STAKE
                    )
            except:
                print('duplicate stake_revenue')

