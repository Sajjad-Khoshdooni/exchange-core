from django.urls import path, include

from stake.views import *

urlpatterns = [
    path('create/', StakeRequestAPIView.as_view({'get': 'list', 'post': 'create'}))
]