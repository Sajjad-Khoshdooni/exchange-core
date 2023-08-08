from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from ledger.models.price_alert import PriceTracking


class AlertViewSerializer(serializers.ModelSerializer):
    def validate(self, data):
        user = self.context['request'].user
        asset = data['asset']
        if PriceTracking.objects.filter(user=user, asset=asset).exists():
            raise ValidationError({'asset': 'بازار انتخاب شده تحت‌نظر می‌باشد.'})
        if asset.is_cash():
            raise ValidationError({'asset': 'بازار انتخاب شده ریالی می‌باشد.'})
        return data

    class Meta:
        model = PriceTracking
        fields = ('asset',)


class AlertView(viewsets.ModelViewSet):
    serializer_class = AlertViewSerializer
    queryset = PriceTracking.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)
