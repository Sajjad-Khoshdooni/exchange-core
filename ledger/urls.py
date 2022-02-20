from django.urls import path

from ledger import views

urlpatterns = [
    path('v1/assets/', views.AssetsViewSet.as_view({'get': 'list'})),
    path('v1/assets/<slug:symbol>/', views.AssetsViewSet.as_view({'get': 'retrieve'})),

    path('v1/wallets/', views.WalletViewSet.as_view({'get': 'list'})),
    path('v1/wallets/<slug:symbol>/', views.WalletViewSet.as_view({'get': 'retrieve'})),
    path('v1/wallets/<slug:symbol>/balance/', views.WalletBalanceView.as_view()),
    path('v1/deposit/address/', views.DepositAddressView.as_view()),

    path('v1/withdraw/', views.WithdrawView.as_view()),

    path('v1/withdraw/list/', views.WithdrawHistoryView.as_view()),
    path('v1/deposit/list/', views.DepositHistoryView.as_view()),

    path('v1/trade/otc/request/', views.OTCTradeRequestView.as_view()),
    path('v1/trade/otc/', views.OTCTradeView.as_view()),
    path('v1/trade/otc/history/', views.OTCHistoryView.as_view()),

    path('v1/margin/info/', views.MarginInfoView.as_view()),
    path('v1/margin/info/<slug:symbol>/', views.AssetMarginInfoView.as_view()),
    path('v1/margin/transfer/', views.MarginTransferView.as_view()),
    path('v1/margin/loan/', views.MarginLoanView.as_view()),
]
