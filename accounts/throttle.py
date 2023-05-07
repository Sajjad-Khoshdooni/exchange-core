import logging

from rest_framework.throttling import UserRateThrottle

from accounts.authentication import CustomTokenAuthentication

logger = logging.getLogger(__name__)


class CustomUserRateThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        from accounts.views.jwt_views import user_has_delegate_permission
        authenticator = getattr(request, 'successful_authenticator', None)
        used_token_authentication = isinstance(authenticator, CustomTokenAuthentication)

        is_delegated = user_has_delegate_permission(request.user) and \
                       getattr(request.auth, 'token_type', None) == 'access' and \
                       hasattr(request.auth, 'payload') and request.auth.payload.get('account_id')

        is_throttle_exempt = used_token_authentication and request.user.auth_token.throttle_exempted

        if request.auth and request.user and (is_delegated or is_throttle_exempt):
            return True

        return super(CustomUserRateThrottle, self).allow_request(request, view)


class BurstRateThrottle(CustomUserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(CustomUserRateThrottle):
    scope = 'sustained'


class BursAPIRateThrottle(CustomUserRateThrottle):
    scope = 'burst_api'


class SustainedAPIRateThrottle(CustomUserRateThrottle):
    scope = 'sustained_api'
