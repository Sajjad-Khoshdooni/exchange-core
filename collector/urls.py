from django.urls import path

from collector.views import PriceGetterView

urlpatterns = [
    path('price/getter/', PriceGetterView.as_view())
]
