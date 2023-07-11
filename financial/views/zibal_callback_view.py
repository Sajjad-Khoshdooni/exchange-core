import logging

from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from financial.models import PaymentRequest
from financial.models.payment import Payment
from ledger.utils.fields import DONE, CANCELED, PENDING

logger = logging.getLogger(__name__)


class ZibalCallbackView(TemplateView):
    authentication_classes = permission_classes = ()

    def get(self, request, *args, **kwargs):

        status = request.GET.get('success')
        authority = request.GET.get('trackId')

        if status not in ['1', '0']:
            return HttpResponseBadRequest('Invalid data')

        payment_request = get_object_or_404(PaymentRequest, authority=authority)
        payment = payment_request.payment

        if not payment:
            with transaction.atomic():
                payment = payment_request.payment = Payment.objects.create(
                    group_id=payment_request.group_id,
                    user=payment_request.bank_card.user,
                    amount=payment_request.amount,
                    fee=payment_request.fee,
                )
                payment_request.save(update_fields=['payment'])

        if payment.status == PENDING:
            if status == '0':
                payment.status = CANCELED
                payment.save(update_fields='status')
            else:
                payment_request.get_gateway().verify(payment)

        print('REDIRECTING', payment.   get_redirect_url())

        return payment.redirect_to_app()
