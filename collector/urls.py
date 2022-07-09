from django.urls import path

from collector.views import CoinPriceView

urlpatterns = [
    path('price/<str:coin>/<str:base>/<str:base>/', CoinPriceView.as_view())
]
