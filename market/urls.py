from django.urls import path
from market.views import MarketInfoView


urlpatterns = [
    path('irt/info/', MarketInfoView.as_view()),
]
