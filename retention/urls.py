from django.urls import path

from retention.views import click_view

urlpatterns = [
    path('click/<slug:token>/', click_view),
]
