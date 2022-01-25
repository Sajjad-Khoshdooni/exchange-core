from rest_framework.exceptions import ValidationError
from rest_framework.generics import CreateAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from ledger.exceptions import InsufficientBalance
from ledger.models import MarginTransfer, Asset
from ledger.utils.margin import get_margin_info


class MarginInfoView(APIView):
    def get(self, request):
        account = request.user.account
        margin_info = get_margin_info(account)

        return Response({
            'total_assets': margin_info.total_assets,
            'total_debt': margin_info.total_debt,
            'margin_level': margin_info.get_margin_level(),
            'total_equity': margin_info.get_total_equity(),
        })


class MarginTransferSerializer(serializers.ModelSerializer):

    def validate(self, attrs):
        symbol = attrs.pop('coin')
        asset = get_object_or_404(Asset, symbol=symbol)

        account = self.context['request'].user.account

        return {**attrs, 'asset': asset, 'account': account}

    class Meta:
        fields = ('coin', 'amount', 'type')
        model = MarginTransfer


class MarginTransferView(CreateAPIView):
    serializer_class = MarginTransferSerializer

    def perform_create(self, serializer):
        try:
            serializer.save()
        except InsufficientBalance:
            raise ValidationError('موجودی کافی نیست.')
