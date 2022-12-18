from django.utils.translation import activate
from rest_framework import serializers
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenObtainSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from decouple import config

from accounts.models import Account
from accounts.authentication import CustomTokenAuthentication


def user_has_delegate_permission(user):
    return str(user.id) in config('DELEGATION_PERMITTED_USERS', '').split(',')


class DelegatedAccountMixin:
    @staticmethod
    def get_account_variant(request):
        if request.auth and request.user and user_has_delegate_permission(request.user) and \
                getattr(request.auth, 'token_type', None) == 'access' and \
                hasattr(request.auth, 'payload') and request.auth.payload.get('account_id'):
            activate('en-US')

            return Account.objects.get(id=request.auth.payload.get('account_id')), request.auth.payload.get('variant')

        if request.user:
            return request.user.account, None
        return None, None


class InternalTokenObtainPairSerializer(serializers.Serializer):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mask'] = serializers.IntegerField(required=True)
        self.fields['variant'] = serializers.CharField(required=True, allow_null=True)

    @classmethod
    def get_token(cls, user, mask=None, variant=None):
        token = RefreshToken.for_user(user)

        account = Account.objects.get(user_id=user.pk)
        if mask and user_has_delegate_permission(user):
            token['account_id'] = mask
            token['variant'] = variant
        else:
            token['account_id'] = account.id

        return token

    def validate(self, attrs):
        mask = attrs.pop('mask', None)
        variant = attrs.pop('variant', None)
        data = super().validate(attrs)

        refresh = self.get_token(self.context['user'], mask, variant)

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


class SessionTokenObtainPairSerializer(CustomTokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super(TokenObtainSerializer, self).__init__(*args, **kwargs)

    def validate(self, attrs):
        refresh = self.get_token(self.context['user'])
        data = {'access': str(refresh.access_token)}
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class SessionTokenObtainPairView(TokenObtainPairView):
    authentication_classes = (SessionAuthentication,)
    permission_classes = (IsAuthenticated,)
    serializer_class = SessionTokenObtainPairSerializer

    def get_serializer_context(self):
        return {
            **super(SessionTokenObtainPairView, self).get_serializer_context(),
            'user': self.request.user
        }


class TokenLogoutView(APIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response(status=status.HTTP_400_BAD_REQUEST)
