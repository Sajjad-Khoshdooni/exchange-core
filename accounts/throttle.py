import logging

from rest_framework.throttling import UserRateThrottle

from accounts.models import CustomToken

logger = logging.getLogger(__name__)


class CustomUserRateThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        from accounts.views.jwt_views import user_has_delegate_permission
        used_token_authentication = isinstance(getattr(request, 'successful_authenticator', None), CustomToken)
        if request.auth and request.user and user_has_delegate_permission(request.user) and ((
                getattr(request.auth, 'token_type', None) == 'access' and
                hasattr(request.auth, 'payload') and request.auth.payload.get('account_id')
        ) or used_token_authentication):
            return True
        allow_request = super(CustomUserRateThrottle, self).allow_request(request, view)
        if not allow_request:
            logger.info(f"throttled {request.auth}, {request.user}, {user_has_delegate_permission(request.user)}, "
                        f"{getattr(request.auth, 'token_type', None) == 'access'}, {hasattr(request.auth, 'payload')}, "
                        f"{used_token_authentication}")
        return allow_request


class BurstRateThrottle(CustomUserRateThrottle):
    scope = 'burst'


class SustainedRateThrottle(CustomUserRateThrottle):
    scope = 'sustained'


class BursAPIRateThrottle(CustomUserRateThrottle):
    scope = 'burst_api'


class SustainedAPIRateThrottle(CustomUserRateThrottle):
    scope = 'sustained_api'
