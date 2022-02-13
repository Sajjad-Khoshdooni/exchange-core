from django.urls import path

from financial.views import PaymentRequestView, ZarinpalCallbackView

urlpatterns = [
    path('payment/request/', PaymentRequestView.as_view()),
    path('payment/callback/zarinpal/', ZarinpalCallbackView.as_view(), name='zarinpal-callback'),
]
