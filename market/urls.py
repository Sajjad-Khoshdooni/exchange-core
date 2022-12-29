from django.urls import path, include
from django.views.decorators.cache import cache_page
from rest_framework import routers

from market.views import *

router = routers.DefaultRouter()
router.register(r'^orders', OrderViewSet, basename='order')
router.register(r'^stop-loss-orders', StopLossViewSet, basename='stop_loss')

urlpatterns = [
    path('irt/info/', cache_page(60)(MarketInfoView.as_view())),
    path('depth/<str:symbol>/', OrderBookAPIView.as_view()),
    path('orders/cancel/', CancelOrderAPIView.as_view()),
    path('symbols/<str:name>/', SymbolDetailedStatsAPIView.as_view()),
    path('symbols/', cache_page(300)(SymbolListAPIView.as_view())),
    path('myTrades/', AccountTradeHistoryView.as_view()),
    path('trades/', TradeHistoryView.as_view()),
    path('tradingview/ohlcv/', OHLCVAPIView.as_view()),
    path('open-orders/', OpenOrderListAPIView.as_view()),
    path('', include(router.urls)),
    path('bookmark/', BookMarkSymbolAPIView.as_view())
]
