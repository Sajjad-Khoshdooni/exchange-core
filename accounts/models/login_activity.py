from django.conf import settings
from django.contrib.sessions.models import Session
from django.db import models, transaction
from django.template import loader
from django.utils import timezone
from accounts.utils import validation
from accounts.models.email_notification import EmailNotification


class LoginActivity(models.Model):
    TABLET, MOBILE, PC, UNKNOWN = 'tablet', 'mobile', 'pc', 'unknown'
    DEVICE_TYPE = ((TABLET, TABLET), (MOBILE, MOBILE), (PC, PC), (UNKNOWN, UNKNOWN))

    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)
    logout_at = models.DateTimeField(null=True, blank=True)
    ip = models.GenericIPAddressField()

    is_sign_up = models.BooleanField(default=False)

    user_agent = models.TextField(blank=True)
    device = models.CharField(blank=True, max_length=200)
    device_type = models.CharField(choices=DEVICE_TYPE, default=UNKNOWN, max_length=16)
    location = models.CharField(blank=True, max_length=200)
    os = models.CharField(blank=True, max_length=200)
    browser = models.CharField(blank=True, max_length=200)
    session = models.OneToOneField(Session, null=True, blank=True, on_delete=models.SET_NULL)
    refresh_token = models.OneToOneField('accounts.RefreshToken', null=True, blank=True, on_delete=models.SET_NULL)
    city = models.CharField(blank=True, max_length=256)
    country = models.CharField(blank=True, max_length=256)
    ip_data = models.JSONField(null=True, blank=True)

    native_app = models.BooleanField(default=False)

    @transaction.atomic
    def destroy(self):
        destroyed = False

        if self.session:
            self.session.delete()
            self.session = None
            destroyed = True

        if self.refresh_token:
            self.refresh_token.log_out()
            self.refresh_token.delete()
            self.refresh_token = None
            destroyed = True

        if not destroyed:
            return

        self.logout_at = timezone.now()
        self.save(update_fields=['logout_at', 'session', 'refresh_token'])

    @staticmethod
    def send_successful_login_message(login_activity):
        user = login_activity.user
        title = "ورود با دستگاه و آی‌پی جدید"
        context = {
            'now': validation.gregorian_to_jalali_datetime_str(timezone.now()),
            'country': login_activity.country,
            'city': login_activity.city,
            'ip': login_activity.ip,
            'brand': settings.BRAND,
            'site_url': settings.PANEL_URL
        }
        content_html = loader.render_to_string(
            'accounts/notif/email/login_successful_message.html',
            context=context)
        content = loader.render_to_string(
            'accounts/notif/email/login_successful_message.txt',
            context=context)
        EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)

    @staticmethod
    def send_unsuccessful_login_message(user):
        title = "ورود ناموفق"
        is_spam = EmailNotification.objects.filter(recipient=user, title=title,
                                                   created__gte=timezone.now() - timezone.timedelta(minutes=5)).exists()
        if not is_spam:
            context = {
                'now': validation.gregorian_to_jalali_datetime_str(timezone.now()),
                'brand': settings.BRAND,
                'site_url': settings.PANEL_URL
            }
            content_html = loader.render_to_string(
                'accounts/notif/email/login_unsuccessful_message.html',
                context=context)
            content = loader.render_to_string(
                'accounts/notif/email/login_unsuccessful_message.txt',
                context=context)
            EmailNotification.objects.create(recipient=user, title=title, content=content, content_html=content_html)

    class Meta:
        verbose_name_plural = verbose_name = "تاریخچه ورود به حساب"
        indexes = [
            models.Index(fields=['user', 'ip', 'browser', 'os'], name="login_activity_idx"),
        ]
