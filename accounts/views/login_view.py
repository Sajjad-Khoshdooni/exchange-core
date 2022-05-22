import logging

from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.models import Session
from rest_framework import serializers, status
from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models.login_activity import LoginActivity
from accounts.utils.ip import get_client_ip

import logging

from accounts.utils.validation import set_login_activity

logger = logging.getLogger(__name__)


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def save(self, **kwargs):
        login = self.validated_data['login']
        password = self.validated_data['password']
        return authenticate(login=login, password=password)


class LoginView(APIView):
    permission_classes = []

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': 1, 'user_id': request.user.id})

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        if user:
            login(request, user)
            set_login_activity(request, user)
            return Response({'msg': 'success', 'code': 0, 'user_id': user.id})

        else:
            return Response({'msg': 'authentication failed', 'code': -1}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'msg': 'success'})


class LoginActivitySerializer(serializers.ModelSerializer):

    class Meta:
        model = LoginActivity
        fields = ('id', 'created', 'ip', 'device', 'os', 'browser',)


class LoginActivityView(ListAPIView):

    pagination_class = LimitOffsetPagination
    serializer_class = LoginActivitySerializer

    def get_queryset(self):
        return LoginActivity.objects.filter(user=self.request.user).order_by('-id')

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['user_agent'] = self.request.user_agent
        return ctx
