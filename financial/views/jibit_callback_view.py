import logging

from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import LoginActivity
from financial.models import PaymentRequest, Payment, Gateway
from financial.utils.payment_id_client import get_payment_id_client
from ledger.utils.fields import CANCELED, PENDING

logger = logging.getLogger(__name__)


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

        if payment.status == PENDING:
            if status == 'FAILED':
                payment.status = CANCELED
                payment.save()
            else:
                payment_request.get_gateway().verify(payment)

        print('REDIRECTING', payment.get_redirect_url())

        return payment.redirect_to_app()


class JibitPaymentIdCallbackView(APIView):
    authentication_classes = permission_classes = ()

    def post(self, request):
        logger.info('jibit paymentId callback %s' % request.data)

        status = request.data['status']

        if status not in ('SUCCESSFUL', 'FAILED'):
            return HttpResponseBadRequest('Invalid data')

        external_ref = request.data['externalReferenceNumber']

        gateway = Gateway.get_active_pay_id_deposit()
        client = get_payment_id_client(gateway)

        login_activity = LoginActivity.from_request(request)

        client.create_payment_request(external_ref, login_activity=login_activity)

        return Response(201)
