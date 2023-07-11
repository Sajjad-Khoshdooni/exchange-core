import logging

from django.db import transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import TemplateView

from financial.models import PaymentRequest
from financial.models.payment import Payment
from ledger.utils.fields import DONE, CANCELED, PENDING

logger = logging.getLogger(__name__)


class ZarinpalCallbackView(TemplateView):
    authentication_classes = permission_classes = ()

    def get(self, request, *args, **kwargs):
        status = request.GET.get('Status')
        authority = request.GET.get('Authority')

        if status not in ['OK', 'NOK']:
            return HttpResponseBadRequest('Invalid data')

        payment_request = get_object_or_404(PaymentRequest, authority=authority)
        payment = getattr(payment_request, 'payment', None)

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
            if status == 'NOK':
                payment.status = CANCELED
                payment.save()
            else:
                payment_request.get_gateway().verify(payment)

        return payment.redirect_to_app()
