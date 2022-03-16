from rest_framework.generics import ListAPIView
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.request import Request

from market.models import FillOrder
from market.serializers.trade_serializer import FillOrderSerializer


class TradeHistoryView(ListAPIView):
    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        return FillOrder.objects.filter(maker_order__wallet__account=self.request.user.account).union(
            FillOrder.objects.filter(taker_order__wallet__account=self.request.user.account), all=True
        ).order_by('-created')

    def get_serializer_context(self):
        return {
            **super(TradeHistoryView, self).get_serializer_context(),
            'account': self.request.user.account
        }

    def list(self, request: Request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)

        result = []
        for index, trade in enumerate(page):
            result.append(FillOrderSerializer(
                instance=trade,
                context={**self.get_serializer_context(), 'index': index}
            ).data)

        return self.get_paginated_response(result)

