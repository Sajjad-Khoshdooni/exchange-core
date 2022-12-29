from rest_framework.throttling import UserRateThrottle


class CustomUserRateThrottle(UserRateThrottle):
    def allow_request(self, request, view):
        from accounts.views.jwt_views import user_has_delegate_permission
        if request.auth and request.user and user_has_delegate_permission(request.user) and \
                getattr(request.auth, 'token_type', None) == 'access' and \
                hasattr(request.auth, 'payload') and request.auth.payload.get('account_id'):
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
