from django.urls import path

from financial.views import PaymentRequestView, ZarinpalCallbackView, BankCardView, PaymentHistoryView, \
    WithdrawRequestView, WithdrawHistoryView, BankAccountView, PaydotirCallbackView, ZibalCallbackView, \
    ProxyPaymentRedirectView, JibitCallbackView

urlpatterns = [
    path('payment/request/', PaymentRequestView.as_view()),
    path('payments/', PaymentHistoryView.as_view()),
    path('payment/go/', ProxyPaymentRedirectView.as_view()),
    path('payment/callback/zarinpal/', ZarinpalCallbackView.as_view(), name='zarinpal-callback'),
    path('payment/callback/paydotir/', PaydotirCallbackView.as_view(), name='paydotir-callback'),
    path('payment/callback/zibal/', ZibalCallbackView.as_view(), name='zibal-callback'),
    path('payment/callback/Jibit/', JibitCallbackView.as_view(), name='Jibit_callback'),
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
    path('withdraw/request/', WithdrawRequestView.as_view({
        'post': 'create',
    })),
    path('withdraw/request/<int:pk>', WithdrawRequestView.as_view({
        'delete': 'destroy'
    })),
    path('withdraw/list/', WithdrawHistoryView.as_view()),
]
