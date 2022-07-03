from rest_framework.exceptions import ValidationError

from accounts.models import Account
from ledger.models import Asset, CloseRequest


def check_margin_view_permission(account: Account, asset: Asset):
    user = account.user

    assert user
    #
    # if user.level < user.LEVEL3:
    #     raise ValidationError('برا استفاده از حساب تعهدی باید احراز هویت سطح ۳ را انجام دهید.')

    if not user.show_margin or not asset.margin_enable:
        raise ValidationError('شما نمی‌توانید این عملیات را انجام دهید.')

    if not user.margin_quiz_pass_date:
        raise ValidationError('شما باید ابتدا به سوالات معاملات تعهدی پاسخ دهید.')

    if CloseRequest.is_liquidating(user.account):
        raise ValidationError('حساب تعهدی شما در حال تسویه خودکار است. فعلا امکان این عملیات وجود ندارد.')
