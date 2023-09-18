from datetime import datetime

from rest_framework_simplejwt.tokens import UntypedToken

from accounts.models import User


class JWTExpiryByPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if 'HTTP_AUTHORIZATION' in request.META:
            token = request.META['HTTP_AUTHORIZATION'].split(' ')[1]
        else:
            token = request.POST and request.POST.get('refresh', '')
        try:
            payload = UntypedToken(token).payload
            user = payload.get('user_id') and User.objects.filter(id=payload.get('user_id')).first()
            if (
                user and
                    ('password_changed_at' in payload.keys() and
                     datetime.fromisoformat(payload['password_changed_at']) < user.password_changed_at or
                     not 'password_changed_at' in payload.keys() and user.password_changed_at
                    )
            ):
                from rest_framework_simplejwt.tokens import RefreshToken as JWTRefreshToken
                JWTRefreshToken(token).blacklist()

        except Exception as e:
            pass

        response = self.get_response(request)
        return response
