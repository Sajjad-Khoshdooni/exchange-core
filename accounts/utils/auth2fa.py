import base64
import hashlib
import hmac
import math
import time
import uuid
import qrcode
from django.conf import settings
from rest_framework.exceptions import ValidationError

from accounts.models import User


def create_qr_code(token: str):
    key = token.encode('ASCII')

    token = base64.b32encode(key)
    relative_path = 'qrcode/{}.png'.format(uuid.uuid4())
    path = settings.MEDIA_ROOT + relative_path
    qr_string = "otpauth://totp/Raastin?config=" + token.decode(
        "utf-8") + "&issuer=raastin.com&algorithm=SHA1&digits=6&period=30"
    img = qrcode.make(qr_string)
    img.save(path)
    return relative_path


def code_2fa_verifier(user_token: str, code_2fa: str):
    length = 6
    step_in_seconds = 30
    t = math.floor(time.time() // step_in_seconds)
    key = str(user_token).encode('ASCII')
    hmac_object = hmac.new(key, t.to_bytes(length=8, byteorder="big"), hashlib.sha1)
    hmac_sha1 = hmac_object.hexdigest()

    # truncate to 6 digits
    offset = int(hmac_sha1[-1], 16)
    binary = int(hmac_sha1[(offset * 2):((offset * 2) + 8)], 16) & 0x7fffffff
    totp = str(binary)[-length:]
    if code_2fa == totp:
        return True
    raise ValidationError('کد دوعاملی نامعتبر است.')


def is_2fa_active_for_user(user: User):
    if not getattr(user, 'auth2fa', None):
        return False
    return user.auth2fa.verified
