from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView

from financial.models import PaymentRequest, Payment


class GibitCallbackView(TemplateView):
    authentication_classes = permission_classes = ()

    def post(self, request, *args, **kwargs):

        status = request.data['status']
        authority = request.data['purchaseId']

        if status != 'SUCCESSFUL':
            return HttpResponseBadRequest('Invalid data')
        else:
            payment_request = get_object_or_404(PaymentRequest, authority=authority)
            payment = getattr(payment_request, 'payment', None)

            if not payment:
                payment = Payment.objects.create(
                    payment_request=payment_request
                )

            payment_request.get_gateway().verify(payment)

            print('REDIRECTING', payment.get_redirect_url())

            return payment.redirect_to_app()

