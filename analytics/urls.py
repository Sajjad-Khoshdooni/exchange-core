from django.urls import path

from analytics import views

urlpatterns = [
    path('request/', views.request_source_analytics),
    path('traffic/', views.get_source_analytics),
]
