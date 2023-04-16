from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework.response import Response

from financial.models import PaymentRequest, Payment, PaymentIdRequest, Gateway, BankAccount, BankPaymentId
from ledger.utils.fields import CANCELED


class JibitCallbackView(TemplateView):
    authentication_classes = permission_classes = ()

    def post(self, request, *args, **kwargs):

        status = request.POST['status']
        authority = request.POST['purchaseId']

        if status not in ('SUCCESSFUL', 'FAILED'):
            return HttpResponseBadRequest('Invalid data')

        payment_request = get_object_or_404(PaymentRequest, authority=authority)
        payment = getattr(payment_request, 'payment', None)

        if not payment:
            payment = Payment.objects.create(
                payment_request=payment_request
            )

        if payment.status == Payment.PENDING:
            if status == 'FAILED':
                payment.status = CANCELED
                payment.save()
            else:
                payment_request.get_gateway().verify(payment)

        print('REDIRECTING', payment.get_redirect_url())

        return payment.redirect_to_app()


class JibitPaymentidCallbackView(TemplateView):
    authentication_classes = permission_classes = ()

    def post(self, request):
        status = request.POST['status']

        if status not in ('SUCCESSFUL', 'FAILED'):
            return HttpResponseBadRequest('Invalid data')

        bank_payment_id = BankPaymentId.objects.get(
            gateway=Gateway.objects.filter(type=Gateway.JIBIT).first(),
            bank_account__id=request.POST['id']
        )

        PaymentIdRequest.objects.create(
            bank_payment_id=bank_payment_id,
            amount=request.POST['amount'],
            bank=request.POST['bank'],
            bank_reference_number=request.POST['bankRefrenceNumber'],
            destination_account_identifier=request.POST['destinationAccountIdentifier'],
            external_reference_number=request.POST['externalRefrenceNumber'],
            payment_id=request.POST['PaymentId'],
            raw_bank_timestamp=request.POST['rawBankTimestamp'],
            status=status
        )
        return Response(200)
