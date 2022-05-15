from django.urls import path, include
from rest_framework import routers

from market.views import *

router = routers.DefaultRouter()
router.register(r'^orders', OrderViewSet, basename='order')
router.register(r'^stop-loss-orders', StopLossViewSet, basename='stop_loss')

urlpatterns = [
    path('irt/info/', MarketInfoView.as_view()),
    path('depth/<str:symbol>/', OrderBookAPIView.as_view()),
    path('orders/cancel/', CancelOrderAPIView.as_view()),
    path('symbols/<str:name>/', SymbolDetailedStatsAPIView.as_view()),
    path('symbols/', SymbolListAPIView.as_view()),
    path('myTrades/', AccountTradeHistoryView.as_view()),
    path('trades/', TradeHistoryView.as_view()),
    path('tradingview/ohlcv/', OHLCVAPIView.as_view()),
    path('', include(router.urls)),
]
