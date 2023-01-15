import logging

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication, get_authorization_header

from accounts.models import CustomToken
from accounts.utils.ip import get_client_ip

logger = logging.getLogger(__name__)


class CustomTokenAuthentication(TokenAuthentication):
    model = CustomToken

    def authenticate(self, request):
        auth = get_authorization_header(request).split()

        if not auth or auth[0].lower() != self.keyword.lower().encode():
            return None
        # activate('en-US')

        if len(auth) == 1:
            msg = _('Invalid token header. No credentials provided.')
            raise exceptions.AuthenticationFailed(msg)
        elif len(auth) > 2:
            msg = _('Invalid token header. Token string should not contain spaces.')
            raise exceptions.AuthenticationFailed(msg)

        try:
            token = auth[1].decode()
        except UnicodeError:
            msg = _('Invalid token header. Token string should not contain invalid characters.')
            raise exceptions.AuthenticationFailed(msg)

        return self.authenticate_credentials(token, request)

    def authenticate_credentials(self, key, request):
        model = self.get_model()
        request_ip = get_client_ip(request=request)
        print('request_ip', request_ip)

        try:
            token = model.objects.select_related('user').get(
                Q(ip_list__contains=[request_ip]) | Q(ip_list__isnull=True),
                key=key,
                type=model.API
            )

        except model.DoesNotExist:
            logger.info(f'requested ip: {request_ip}')
            raise exceptions.AuthenticationFailed(_('Invalid token.'))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_('User inactive or deleted.'))

        return (token.user, token)
