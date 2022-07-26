import logging

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound

from market.models import CancelRequest, Order, StopLoss
from market.utils import cancel_order

logger = logging.getLogger(__name__)


class CancelRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='order.id')
    canceled_at = serializers.CharField(source='created', read_only=True)

    @staticmethod
    def cancel_order(order: Order, validated_data):
        try:
            with transaction.atomic():
                cancel_request = cancel_order(order)
        except Exception as e:
            logger.error('failed canceling order', extra={'exp': e, 'order': validated_data})
            if settings.DEBUG:
                raise e
            raise APIException(_('Could not cancel order'))
        return cancel_request

    def create(self, validated_data):
        instance_id = validated_data.pop('order')['id']
        if instance_id.startswith('sl-'):
            stop_loss = StopLoss.open_objects.filter(
                wallet__account=self.context['account'],
                id=instance_id.split('sl-')[1],
            ).first()
            if not stop_loss:
                raise NotFound(_('StopLoss not found'))
            with transaction.atomic():
                stop_loss.delete()
                order = stop_loss.order_set.first()
                if order:
                    return self.cancel_order(order, validated_data)
                else:
                    # faking cancel request creation
                    fake_order = Order(id=instance_id)
                    return CancelRequest(order=fake_order, created=timezone.now())
        else:
            order = Order.open_objects.filter(
                wallet__account=self.context['account'],
                id=instance_id,
            ).first()
            if not order or order.stop_loss:
                raise NotFound(_('Order not found'))

        return self.cancel_order(order, validated_data)

    class Meta:
        model = CancelRequest
        fields = ('id', 'canceled_at')
