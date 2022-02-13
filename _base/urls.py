from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/media/', include('multimedia.urls')),
    path('api/v1/finance/', include(('financial.urls', 'financial'), 'finance', )),
    path('api/', include('ledger.urls')),
    path('hijack/', include('hijack.urls')),
    path('robots.txt', TemplateView.as_view(template_name="robots.txt", content_type="text/plain")),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
