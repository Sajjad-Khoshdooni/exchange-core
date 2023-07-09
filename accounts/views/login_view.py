import logging

from django.contrib.auth import authenticate, login, logout
from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from _base import settings
from accounts.models.email_notification import EmailNotification
from accounts.models.login_activity import LoginActivity
from accounts.models.user import User
from accounts.utils.validation import set_login_activity
from accounts.views.user_view import UserSerializer

logger = logging.getLogger(__name__)


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def save(self, **kwargs):
        login = self.validated_data['login'].lower()
        password = self.validated_data['password']
        return authenticate(login=login, password=password)


class LoginView(APIView):
    permission_classes = []

    def post(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user).data)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()
        def spam_check(target_user, title):
            return (timezone.now() - EmailNotification.objects.filter(recipient=target_user, title=title).order_by('-created').first().created).total_seconds() > 300
        if user:
            login(request, user)
            set_login_activity(request, user)
            login_status = LoginActivity.objects.filter(user=user).order_by('-created').first()
            if LoginActivity.objects.filter(user=user, device=login_status.device,os=login_status.os,ip=login_status.ip).count() == 1:
                body = \
                f'''
                <p>
     شما از دستگاه جدیدی به حساب کاربری خود وارد شده اید.           
                تاریخ:
                 {login_status.created}
                مکان:
                {login_status.country} / {login_status.city}
                آی پی:
                {login_status.ip}
                <a href="https://raastin.com/account/security">تغییر رمز عبور</a>
                {settings.BRAND}
                </p>'''
                EmailNotification.objects.create(recipient=user, title="ورود موفق", content=body, content_html="")
            return Response(UserSerializer(user).data)
        else:
            user = User.objects.filter(phone=serializer.data['login']).first()
            if user and spam_check(user, "ورود ناموفق"):
                body = f'''
                <p>
                 ورود ناموفق به حساب کاربری
                زمان:
                {timezone.now()}
                <a href="https://raastin.com/account/security">
                    تغییر رمز عبور
                </a>
                {settings.BRAND}
                </p>'''
                EmailNotification.objects.create(recipient=user, title="ورود ناموفق", content=body, content_html="")
            return Response({'msg': 'authentication failed', 'code': -1}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'msg': 'success'})


class LoginActivitySerializer(serializers.ModelSerializer):
    active = serializers.SerializerMethodField()
    current = serializers.SerializerMethodField()

    def get_active(self, login_activity: LoginActivity):
        session = login_activity.session
        return (session and session.expire_date > timezone.now()) or not login_activity.refresh_token is None

    def get_current(self, login_activity: LoginActivity):
        session = login_activity.session
        return session and session.session_key == self.context['request'].session.session_key

    class Meta:
        model = LoginActivity
        fields = ('id', 'created', 'ip', 'device', 'os', 'browser', 'session', 'active', 'current')


class LoginActivityViewSet(ModelViewSet):

    pagination_class = LimitOffsetPagination
    serializer_class = LoginActivitySerializer

    def get_queryset(self, only_active: bool = False):
        logins = LoginActivity.objects.filter(user=self.request.user).order_by('-id')

        if only_active or self.request.query_params.get('active') == '1':
            logins = logins.filter(
                Q(session__isnull=False, session__expire_date__gt=timezone.now()) |
                Q(refresh_token__isnull=False)
            )

        return logins

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        ctx['user_agent'] = self.request.user_agent
        return ctx

    def perform_destroy(self, instance: LoginActivity):
        if (instance.session and self.request.session.session_key != instance.session.session_key) or \
                instance.refresh_token:
            instance.destroy()

    def destroy_all(self, request, *args, **kwargs):
        to_delete_sessions = self.get_queryset(only_active=True)

        session_key = request.session and request.session.session_key
        if session_key:
            to_delete_sessions = to_delete_sessions.exclude(
                session__session_key=request.session.session_key
            )

        for login_activity in to_delete_sessions:
            login_activity.destroy()

        return Response(status=status.HTTP_204_NO_CONTENT)
