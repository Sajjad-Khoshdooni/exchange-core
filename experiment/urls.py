from django.urls import path
from experiment.views import *

urlpatterns = [
    path('click/<slug:token>/', click_view),
]
