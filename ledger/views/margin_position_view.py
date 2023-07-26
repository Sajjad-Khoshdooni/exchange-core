from rest_framework.viewsets import ModelViewSet

from ledger.models import MarginPosition
from ledger.models.asset import AssetSerializerMini


class MarginPositionSerializer(AssetSerializerMini):
    class Meta:
        model = MarginPosition
        fields = ('created', 'account', 'wallet', 'symbol', 'amount', 'average_price', 'liquidation_price', 'side',
                  'status')


class MarginPositionViewSet(ModelViewSet):
    serializer_class = MarginPositionSerializer

    def get_queryset(self):
        return MarginPosition.objects.filter(account=self.request.user.get_account())
