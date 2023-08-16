from rest_framework.routers import DefaultRouter
from django.urls import path, include
from ledger import views

router = DefaultRouter()
router.register(r'', viewset=views.AssetAlertView)

urlpatterns = [
    path('v1/assets/', views.AssetsViewSet.as_view({'get': 'list'})),
    path('v1/assets/categories/', views.CoinCategoryListView.as_view()),
    path('v1/networkassets/', views.NetworkAssetView.as_view()),
    path('v1/asset/overview/', views.AssetOverviewAPIView.as_view()),
    path('v1/assets/alert/', include(router.urls)),

    path('v1/networks/', views.BriefNetworkAssetsView.as_view()),

    path('v1/assets/reserve/', views.ReserveWalletCreateAPIView.as_view()),
    path('v1/assets/reserve/refund/', views.ReserveWalletRefundAPIView.as_view()),

    path('v1/assets/<slug:symbol>/', views.AssetsViewSet.as_view({'get': 'retrieve'})),

    path('v1/wallets/', views.WalletViewSet.as_view({'get': 'list'})),
    path('v1/wallets/<slug:symbol>/', views.WalletViewSet.as_view({'get': 'retrieve'})),
    path('v1/wallets/<slug:symbol>/balance/', views.WalletBalanceView.as_view()),
    path('v1/deposit/address/', views.DepositAddressView.as_view()),

    path('v1/withdraw/', views.WithdrawView.as_view()),

    path('v1/withdraws/', views.WithdrawViewSet.as_view({
        'get': 'list'
    })),
    path('v1/withdraws/<int:pk>/', views.WithdrawViewSet.as_view({
        'delete': 'destroy'
    })),

    path('v1/withdraw/list/', views.WithdrawHistoryView.as_view()),
    path('v1/deposit/list/', views.DepositHistoryView.as_view()),

    path('v1/trade/otc/request/', views.OTCTradeRequestView.as_view()),
    path('v1/trade/otc/', views.OTCTradeView.as_view()),
    path('v1/trade/otc/info/', views.OTCInfoView.as_view()),
    path('v1/trade/otc/myTrades/', views.OTCHistoryView.as_view()),

    path('v1/margin/info/', views.MarginInfoView.as_view()),
    path('v1/margin/info/<slug:symbol>/', views.AssetMarginInfoView.as_view()),
    path('v1/margin/transfer/', views.MarginTransferViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),

    path('v1/margin/wallets/', views.MarginWalletViewSet.as_view({'get': 'list'})),
    path('v1/margin/close/', views.MarginClosePositionView.as_view()),
    path('v1/margin/loan/', views.MarginLoanViewSet.as_view({
        'get': 'list',
        'post': 'create'
    })),

    path('v1/addressbook/<int:pk>/', views.AddressBookView.as_view({
        'get': 'retrieve',
        'delete': 'destroy',
    })),
    path('v1/addressbook/', views.AddressBookView.as_view({
        'post': 'create',
        'get': 'list',
    })),
    path('v2/addressbook/', views.AddressBookViewV2.as_view({
        'post': 'create',
        'get': 'list',
    })),

    path('v1/wallet/balance/', views.BalanceInfoView.as_view()),
    path('v1/funds/overview/', views.WalletsOverviewAPIView.as_view()),
    path('v1/bookmark/assets/', views.BookmarkAssetsAPIView.as_view()),

    path('v1/transfer/deposit/', views.DepositTransferUpdateView.as_view()),
    path('v1/transfer/withdraw/', views.WithdrawTransferUpdateView.as_view()),

    path('v1/convert/dust/', views.ConvertDustView.as_view()),
    path('v1/bookmark/assets/', views.BookmarkAssetsAPIView.as_view()),
    path('v1/pnl/overview/', views.PNLOverview.as_view()),

    path('v1/fast_buy/', views.FastBuyTokenAPI.as_view()),
]
