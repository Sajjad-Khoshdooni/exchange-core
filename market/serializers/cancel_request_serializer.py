import logging

from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound, PermissionDenied

from ledger.utils.wallet_pipeline import WalletPipeline
from market.models import CancelRequest, Order, StopLoss

logger = logging.getLogger(__name__)


class CancelRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='order_id')
    canceled_at = serializers.CharField(source='created', read_only=True)

    @staticmethod
    def cancel_order(order: Order, validated_data):
        try:
            with transaction.atomic():
                req, created = CancelRequest.objects.get_or_create(order_id=order.id)
                if created:
                    order.cancel()
        except Exception as e:
            logger.error('failed canceling order', extra={'exp': e, 'order': validated_data})
            if settings.DEBUG_OR_TESTING_OR_STAGING:
                raise e
            raise APIException(_('Could not cancel order'))
        return req

    def create(self, validated_data):
        instance_id = validated_data.pop('order_id')
        if instance_id.startswith('sl-'):
            stop_loss = StopLoss.open_objects.filter(
                wallet__account=self.context['account'],
                id=instance_id.split('sl-')[1],
            ).first()
            if not stop_loss:
                raise NotFound(_('StopLoss not found'))
            if stop_loss.wallet.variant and not self.context['allow_cancel_strategy_orders']:
                raise PermissionDenied({'message': _('You do not have permission to perform this action.'), })
            with WalletPipeline() as pipeline:
                stop_loss.delete()
                order = stop_loss.order_set.first()
                if order:
                    return self.cancel_order(order, validated_data)
                else:
                    if stop_loss.price:
                        order_price = stop_loss.price
                    else:
                        conservative_factor = Decimal('1.01') if stop_loss.side == Order.BUY else Decimal(1)
                        order_price = stop_loss.trigger_price * conservative_factor

                    release_amount = Order.get_to_lock_amount(
                        stop_loss.unfilled_amount, order_price, stop_loss.side
                    )
                    pipeline.release_lock(key=stop_loss.group_id, amount=release_amount)
                    # faking cancel request creation
                    return CancelRequest(order_id=instance_id, created=timezone.now())
        else:
            order = Order.open_objects.filter(
                wallet__account=self.context['account'],
                id=instance_id,
            ).first()
            if not order or order.stop_loss:
                raise NotFound(_('Order not found'))
            if order.wallet.variant and not self.context['allow_cancel_strategy_orders']:
                raise PermissionDenied({'message': _('You do not have permission to perform this action.'), })

        return self.cancel_order(order, validated_data)

    class Meta:
        model = CancelRequest
        fields = ('id', 'canceled_at')
