from accounts.models import VerificationCode


def generate_otp_code(scope, phone, user) -> VerificationCode:
    otp_code = VerificationCode.objects.create(
        phone=phone,
        scope=scope,
        code='1',
        user=user
        )
    return otp_code.code
