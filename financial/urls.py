from django.urls import path

from financial.views import PaymentRequestView, ZarinpalCallbackView, BankCardView

urlpatterns = [
    path('payment/request/', PaymentRequestView.as_view()),
    path('payment/callback/zarinpal/', ZarinpalCallbackView.as_view(), name='zarinpal-callback'),
    path('cards/', BankCardView.as_view()),
]
