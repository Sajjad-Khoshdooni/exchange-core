from django.urls import path, include

from stake.views import *

urlpatterns = [
    path('request/', StakeRequestAPIView.as_view({'get': 'list', 'post': 'create'})),
    path('delete/<int:pk>/', StakeRequestAPIView.as_view({'delete': 'destroy'})),
    path('option/', StakeOptionAPIView.as_view()),
    path('revenue/', StakeRevenueAPIView.as_view()),
]
