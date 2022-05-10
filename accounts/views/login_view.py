from django.contrib.auth import authenticate, login, logout
from django.contrib.sessions.models import Session

from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from accounts.utils.ip import get_client_ip
from django.contrib.gis.geoip2 import GeoIP2
from accounts.models.login_activity import LoginActivity


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
            LoginActivity.objects.create(
                user=user,
                ip=get_client_ip(request),
                user_agent=request.META['HTTP_USER_AGENT'],
                session=Session.objects.get(session_key=request.session.session_key),
                device=request.user_agent.device,
                os=request.user_agent.os,
                browser=request.user_agent.browser,
            )
            return Response({'msg': 'success', 'code': 0, 'user_id': user.id})

        else:
            return Response({'msg': 'authentication failed', 'code': -1}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'msg': 'success'})


class LoginActivitySerializer(serializers.ModelSerializer):
    device = serializers.SerializerMethodField()
    os = serializers.SerializerMethodField()
    browser = serializers.SerializerMethodField()

    def get_device(self, instance):
        user_agent = self.context['user_agent']
        return user_agent.device.family

    def get_os(self, instance):
        user_agent = self.context['user_agent']
        response = user_agent.os.family
        if user_agent.os.version_string:
            response += ' ' + user_agent.os.version_string
        return response

    def get_browser(self, instance):
        user_agent = self.context['user_agent']
        response = user_agent.browser.family
        if response:
            response += ' ' + user_agent.browser.version_string
        return response

    class Meta:
        model = LoginActivity
        fields = ('id', 'created', 'ip', 'device', 'os', 'browser',)


class LoginActivityView(ListAPIView):

    serializer_class = LoginActivitySerializer

    def get_queryset(self):
        query_set = LoginActivity.objects.filter(user=self.request.user)
        return query_set

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['user_agent'] = self.request.user_agent
        return ctx