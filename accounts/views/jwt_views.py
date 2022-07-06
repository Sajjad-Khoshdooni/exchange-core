from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from yekta_config import secret

from accounts.models import Account
from accounts.views.authentication import CustomTokenAuthentication


def user_has_delegate_permission(user):
    return str(user.id) in secret('delegation_permitted_users').split(',')


class DelegatedAccountMixin:
    @staticmethod
    def get_account(request):
        if request.auth and request.user and user_has_delegate_permission(request.user) and \
                getattr(request.auth, 'token_type', None) == 'access' and \
                hasattr(request.auth, 'payload') and request.auth.payload.get('account_id'):
            return Account.objects.get(id=request.auth.payload.get('account_id'))

        if request.user:
            return request.user.account


class InternalTokenObtainPairSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mask'] = serializers.IntegerField(required=True)

    @classmethod
    def get_token(cls, user, mask=None):
        token = RefreshToken.for_user(user)

        account = Account.objects.get(user_id=user.pk)
        if mask and user_has_delegate_permission(user):
            token['account_id'] = mask
        else:
            token['account_id'] = account.id

        return token

    def validate(self, attrs):
        mask = attrs.pop('mask', None)
        data = super().validate(attrs)

        refresh = self.get_token(self.context['user'], mask)

        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data


class InternalTokenObtainPairView(TokenObtainPairView):
    authentication_classes = (CustomTokenAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = InternalTokenObtainPairSerializer

    def get_serializer_context(self):
        return {
            **super(InternalTokenObtainPairView, self).get_serializer_context(),
            'user': self.request.user
        }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        account = Account.objects.get(user_id=user.pk)
        token['account_id'] = account.id

        return token


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
