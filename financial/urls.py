from django.urls import path

from financial.views import PaymentRequestView, ZarinpalCallbackView, BankCardView, PaymentHistoryView, \
    WithdrawRequestView, WithdrawHistoryView, BankAccountView

urlpatterns = [
    path('payment/request/', PaymentRequestView.as_view()),
    path('payments/', PaymentHistoryView.as_view()),
    path('payment/callback/zarinpal/', ZarinpalCallbackView.as_view(), name='zarinpal-callback'),
    path('cards/', BankCardView.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('cards/<int:pk>/', BankCardView.as_view({
        'get': 'retrieve',
        'delete': 'destroy'
    })),
    path('accounts/', BankAccountView.as_view({
        'get': 'list',
        'post': 'create'
    })),
    path('accounts/<int:pk>/', BankAccountView.as_view({
        'get': 'retrieve',
        'delete': 'destroy'
    })),
    path('withdraw/request/', WithdrawRequestView.as_view()),
    path('withdraw/list/', WithdrawHistoryView.as_view()),
]
