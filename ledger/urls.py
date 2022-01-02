from django.urls import path
from ledger import views


urlpatterns = [
    path('v1/general/assets/', views.GeneralAssetInfoView.as_view()),
    path('v1/wallet/', views.WalletView.as_view()),
    path('v1/wallet/address/', views.WalletAddressView.as_view()),
    path('v1/trade/otc/request/', views.OTCTradeRequestView.as_view()),
    path('v1/trade/otc/trade/', views.OTCTradeView.as_view()),
]
