import logging

from django.conf import settings
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.exceptions import APIException, NotFound

from market.models import CancelRequest, Order

logger = logging.getLogger(__name__)


class CancelRequestSerializer(serializers.ModelSerializer):
    id = serializers.CharField(source='order.id')
    canceled_at = serializers.CharField(source='created', read_only=True)

    def create(self, validated_data):
        order = Order.open_objects.filter(
            wallet__account=self.context['account'],
            id=validated_data.pop('order')['id'],
        ).first()
        if not order:
            raise NotFound(_('Order not found'))

        try:
            with transaction.atomic():
                created_cancel_request = super(CancelRequestSerializer, self).create({**validated_data, 'order': order})
                Order.cancel_orders(order.symbol)
        except Exception as e:
            logger.error('failed canceling order', extra={'exp': e, 'order': validated_data})
            if settings.DEBUG:
                raise e
            raise APIException(_('Could not cancel order'))

        return created_cancel_request

    class Meta:
        model = CancelRequest
        fields = ('id', 'canceled_at')
