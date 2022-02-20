from django.urls import path

from financial.views import PaymentRequestView, ZarinpalCallbackView, BankCardView, PaymentHistoryView
from financial.views.withdraw_request_view import WithdrawRequestView

urlpatterns = [
    path('payment/request/', PaymentRequestView.as_view()),
    path('payments/', PaymentHistoryView.as_view()),
    path('payment/callback/zarinpal/', ZarinpalCallbackView.as_view(), name='zarinpal-callback'),
    path('cards/', BankCardView.as_view()),
    path('withdraw/request/', WithdrawRequestView.as_view()),
]
