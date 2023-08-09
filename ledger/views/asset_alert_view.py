from rest_framework import viewsets
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError

from ledger.models.asset import AssetSerializerMini
from ledger.models.asset_alert import AssetAlert


class AssetAlertViewSerializer(serializers.ModelSerializer):
    asset = AssetSerializerMini(read_only=['margin_enable', 'precision', 'step_size', 'name', 'name_fa',
                                           'logo', 'original_symbol', 'original_name_fa'])

    def validate(self, data):
        user = self.context['request'].user
        asset = data['asset']
        if AssetAlert.objects.filter(user=user, asset=asset).exists():
            raise ValidationError({'asset': 'ارز دیجیتال انتخاب شده تحت‌نظر می‌باشد.'})
        if asset.is_cash():
            raise ValidationError({'asset': 'ارزدیجیتال انتخاب شده نباید تومان باشد.'})
        return data

    class Meta:
        model = AssetAlert
        fields = ('asset',)


class AssetAlertView(viewsets.ModelViewSet):
    serializer_class = AssetAlertViewSerializer
    queryset = AssetAlert.objects.all()

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
