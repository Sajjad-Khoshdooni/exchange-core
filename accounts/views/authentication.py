from rest_framework.authentication import TokenAuthentication
from accounts.models import CustomToken
from rest_framework import exceptions
from django.utils.translation import gettext_lazy as _


class CustomTokenAuthentication(TokenAuthentication):
    model = CustomToken

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related('user').get(key=key)
            user = token.user

        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return (token.user, token)
