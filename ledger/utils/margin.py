from rest_framework.exceptions import ValidationError

from accounts.models import Account, User
from accounts.tasks import send_message_by_kavenegar
from ledger.models import Asset, CloseRequest, Wallet, Trx
from ledger.utils.wallet_pipeline import WalletPipeline


def check_margin_view_permission(account: Account, asset: Asset):
    user = account.user

    assert user

    # if user.level < user.LEVEL3:
    #     raise ValidationError('برا استفاده از حساب تعهدی باید احراز هویت سطح ۳ را انجام دهید.')

    if not user.show_margin or not asset.margin_enable:
        raise ValidationError('شما نمی‌توانید این عملیات را انجام دهید.')

    if not user.margin_quiz_pass_date:
        raise ValidationError('لطفا ابتدا به سوالات آزمون معاملات تعهدی پاسخ دهید.')

    if CloseRequest.is_liquidating(user.account):
        raise ValidationError('حساب تعهدی شما در حال تسویه خودکار است. فعلا امکان این عملیات وجود ندارد.')


def close_margin_account(user: User):
    if not user.show_margin:
        return

    close_request = CloseRequest.close_margin(user.account, reason=CloseRequest.SYSTEM)

    if not close_request:
        return

    with WalletPipeline() as pipeline:
        for wallet in Wallet.objects.filter(account=user.account, balance__gt=0, market=Wallet.MARGIN):
            pipeline.new_trx(
                sender=wallet,
                receiver=wallet.asset.get_wallet(wallet.account),
                amount=wallet.balance,
                group_id=close_request.group_id,
                scope=Trx.CLOSE_MARGIN,
            )

    user.show_margin = False
    user.save(update_fields=['show_margin'])

    send_message_by_kavenegar(
        phone=user.phone,
        template='disable-margin',
        token='تعهدی'
    )
