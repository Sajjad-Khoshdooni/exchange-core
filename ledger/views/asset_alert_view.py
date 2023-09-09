from rest_framework import viewsets
from rest_framework.views import APIView
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveUpdateAPIView

from accounts.models import User
from ledger.views.coin_category_list_view import CoinCategorySerializer
from ledger.models.asset import AssetSerializerMini
from ledger.models import AssetAlert, BulkAssetAlert


class AssetAlertViewSerializer(serializers.ModelSerializer):
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


class AssetAlertObjectSerializer(serializers.ModelSerializer):
    asset = AssetSerializerMini()

    class Meta:
        model = AssetAlert
        fields = ('asset',)


class BulkAssetAlertViewSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        user = self.context['request'].user
        subscription_type = attrs['subscription_type']

        if subscription_type == BulkAssetAlert.CATEGORY_COIN_CATEGORIES:
            coin_category = attrs.get('coin_category', None)
            if not coin_category:
                raise ValidationError({'coin_category': 'دسته بندی انتخاب نشده است.'})
        else:
            coin_category = None
        attrs['coin_category'] = coin_category
        if BulkAssetAlert.objects.filter(
                user=user,
                subscription_type=subscription_type,
                coin_category=coin_category
        ).exists():
            raise ValidationError({'bulk_asset': 'دسته بندی انتخاب شده تحت‌نظر می‌باشد.'})
        return attrs

    class Meta:
        model = BulkAssetAlert
        fields = ('subscription_type', 'coin_category',)
        extra_kwargs = {
            'coin_category': {'required': False, 'write_only': True},
        }


class BulkAssetAlertObjectSerializer(serializers.ModelSerializer):
    coin_category = CoinCategorySerializer()

    class Meta:
        model = BulkAssetAlert
        fields = ('subscription_type', 'coin_category',)


class AssetAlertViewSet(viewsets.ModelViewSet):
    serializer_class = AssetAlertViewSerializer
    queryset = AssetAlert.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = AssetAlertObjectSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = AssetAlertObjectSerializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class BulkAssetAlertViewSet(viewsets.ModelViewSet):
    serializer_class = BulkAssetAlertViewSerializer
    queryset = BulkAssetAlert.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = BulkAssetAlertObjectSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = BulkAssetAlertObjectSerializer(instance)
        return Response(serializer.data)

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user
        )

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)


class PriceNotifSwitchSerializer(serializers.ModelSerializer):
    is_price_notif_on = serializers.BooleanField()

    class Meta:
        model = User
        fields = ('is_price_notif_on',)


class PriceNotifSwitchView(RetrieveUpdateAPIView):
    serializer_class = PriceNotifSwitchSerializer

    def get_object(self):
        return self.request.user
