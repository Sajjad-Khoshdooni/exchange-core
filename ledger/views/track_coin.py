from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from ledger.models.price_alert import PriceTracking


class AlertViewSerializer(serializers.ModelSerializer):
    def is_valid(self, raise_exception=True):
        user = self.context['request'].user
        data = self.data
        asset = data['asset']
        if PriceTracking.objects.filter(user=user, asset=asset).exists():
            raise ValidationError('بازار انتخاب شده تحت‌نظر می‌باشد.')
        return data

    class Meta:
        model = PriceTracking
        fields = ('asset',)


class AlertView(viewsets.ModelViewSet):
    serializers_class = AlertViewSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid()
        serializer.perform_create()
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
