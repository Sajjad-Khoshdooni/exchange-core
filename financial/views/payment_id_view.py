from rest_framework.generics import get_object_or_404
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers

from financial.models import PaymentId, Gateway
from financial.utils.payment_id_client import JibitClient


class PaymentIdSerializer(serializers.ModelSerializer):

    def create(self, validated_data):
        user = self.context['request'].user
        gateway = Gateway.get_active_pay_id_deposit()

        client = JibitClient(gateway)

        resp = client.create_payment_id(user)

    class Meta:
        model = PaymentId
        fields = ('pay_id', )


class PaymentIdViewsSet(ModelViewSet):
    serializer_class = PaymentIdSerializer

    def get_object(self):
        gateway = Gateway.get_active_pay_id_deposit()
        return get_object_or_404(PaymentId, user=self.request.user, gateway=gateway)
