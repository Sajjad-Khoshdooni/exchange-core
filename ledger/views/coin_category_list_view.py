from rest_framework import serializers
from rest_framework.generics import ListAPIView

from ledger.models import CoinCategory


class CoinCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CoinCategory
        fields = ('name', 'title', 'description', 'header')


class CoinCategoryListView(ListAPIView):
    permission_classes = ()
    serializer_class = CoinCategorySerializer
    queryset = CoinCategory.objects.all()
