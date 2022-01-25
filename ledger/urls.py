from django.urls import path
from ledger import views


urlpatterns = [
    path('v1/assets/', views.AssetsView.as_view()),

    path('v1/wallets/', views.WalletView.as_view({'get': 'list'})),
    path('v1/wallets/<slug:symbol>/', views.WalletView.as_view({'get': 'retrieve'})),
    path('v1/deposit/address/', views.DepositAddressView.as_view()),

    path('v1/trade/otc/request/', views.OTCTradeRequestView.as_view()),
    path('v1/trade/otc/', views.OTCTradeView.as_view()),

    path('v1/margin/info/', views.MarginInfoView.as_view()),
]
