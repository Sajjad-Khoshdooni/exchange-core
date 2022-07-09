from django.urls import path

from collector.views import CoinPriceView

urlpatterns = [
    path('price/', CoinPriceView.as_view())
]
