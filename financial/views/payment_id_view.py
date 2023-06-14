from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet

from financial.models import PaymentId, Gateway
from financial.utils.payment_id_client import get_payment_id_client


class PaymentIdSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        user = self.context['request'].user
        gateway = Gateway.get_active_pay_id_deposit()

        client = get_payment_id_client(gateway)

        return client.create_payment_id(user)

    class Meta:
        model = PaymentId
        fields = ('pay_id', )
        read_only_fields = ('pay_id', )


class PaymentIdViewsSet(ModelViewSet):
    serializer_class = PaymentIdSerializer

    def get_object(self):
        gateway = Gateway.get_active_pay_id_deposit()
        return get_object_or_404(PaymentId, user=self.request.user, gateway=gateway)
