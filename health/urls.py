from django.urls import path

from health import views

urlpatterns = [
    path('ready/', views.HealthView.as_view()),
]
