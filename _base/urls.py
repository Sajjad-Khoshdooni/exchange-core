from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from yekta_config.config import config

from accounts.views.dashboard import dashboard
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
    openapi.Info(
        title="RAASTIN API",
        default_version='v1',
        description="description",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@snippets.local"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/media/', include('multimedia.urls')),
    path('api/v1/finance/', include(('financial.urls', 'financial'), 'finance', )),
    path('api/v1/market/', include('market.urls')),
    path('api/', include('ledger.urls')),
    path('hijack/', include('hijack.urls')),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),
    path('dashboard/', dashboard),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if config('SHOW_SWAGGER', default=False, cast=bool):
    urlpatterns += [
        re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0),
            name='schema-json'),
        re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
        re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    ]