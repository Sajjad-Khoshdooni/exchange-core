from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/', include('ledger.urls')),
    path('summernote/', include('django_summernote.urls')),
    path('hijack/', include('hijack.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
