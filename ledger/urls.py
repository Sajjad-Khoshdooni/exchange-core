from django.urls import path
from ledger import views


urlpatterns = [
    path('v1/assets/', views.GeneralAssetInfoView.as_view()),
    path('v1/wallets/', views.WalletView.as_view()),
    path('v1/wallets/address/', views.WalletAddressView.as_view()),
    path('v1/trade/otc/request/', views.OTCTradeRequestView.as_view()),
    path('v1/trade/otc/', views.OTCTradeView.as_view()),
]
