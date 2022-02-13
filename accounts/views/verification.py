from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers

from accounts.models import BasicAccountInfo
from accounts.models.bank_card import BankCard, BankCardSerializer


class BankCardListSerializer(serializers.ListSerializer):
    child = BankCardSerializer()


class BasicInfoSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source='user.first_name')
    last_name = serializers.CharField(source='user.last_name')

    def update(self, instance: BasicAccountInfo, validated_data):
        if instance.status in (BasicAccountInfo.PENDING, BasicAccountInfo.VERIFIED):
            raise ValidationError('امکان تغییر اطلاعات وجود ندارد.')

        user = instance.user

        cards_data = self.context['request'].data.get('cards', [])
        to_create_cards = list(filter(lambda d: not d.get('id'), cards_data))
        current_verified_cards = BankCard.objects.filter(user=user, verified=True)
        current_unverified_cards = BankCard.objects.filter(user=user, verified=False)

        if len(to_create_cards) + len(current_verified_cards)  > 3:
            raise ValidationError('حداکثر ۳ تا کارت می‌توانید داشته باشید.')

        to_not_create_card_ids = list(map(lambda x: x['id'], filter(lambda d: d.get('id'), cards_data)))

        to_delete_cards = list(filter(lambda d: d.id not in to_not_create_card_ids, current_unverified_cards))

        cards_serializer = BankCardListSerializer(data=to_create_cards)
        cards_serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user.first_name = self.validated_data['user']['first_name']
            user.last_name = self.validated_data['user']['last_name']
            user.save()

            instance = super().update(instance, validated_data)
            cards_serializer.save(user=user)

            for to_delete in to_delete_cards:
                to_delete.delete()

        return instance

    @property
    def data(self):
        _data = super(BasicInfoSerializer, self).data
        cards = BankCard.objects.filter(user=self.context['request'].user)
        _data['cards'] = BankCardListSerializer(instance=cards).data
        return _data

    class Meta:
        model = BasicAccountInfo
        fields = ('status', 'first_name', 'last_name', 'gender', 'birth_date', 'national_card_code',
                  'national_card_image')

        read_only_fields = ('status', )


class BasicInfoVerificationViewSet(ModelViewSet):
    serializer_class = BasicInfoSerializer

    def get_object(self):
        user = self.request.user
        info, _ = BasicAccountInfo.objects.get_or_create(user=user)
        return info

    def perform_update(self, serializer):
        serializer.save(user=self.request.user)


class VerifySearchLine(APIView):

    def get(self, request):
        return Response('ok!')
