import uuid

from django.db import models

from accounts.models import User


class Auth2Fa(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='auth2fa')
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    qrcode = models.ImageField(upload_to='qrcode')
    verified = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'رمز دوعاملی'
        verbose_name_plural = 'رمز دوعاملی'
