import re

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from ledger.models import AddressBook, Asset, Network


class AddressBookSerializer(serializers.ModelSerializer):
    account = serializers.CharField(read_only=True)
    asset = serializers.CharField(read_only=True)
    network = serializers.CharField()
    coin = serializers.CharField(write_only=True, required=False, default=None)
    deleted = serializers.BooleanField(read_only=True)

    def validate(self, attrs):
        user = self.context['request'].user
        account = user.account
        name = attrs['name']
        address = attrs['address']
        network = get_object_or_404(Network, symbol=attrs['network'])

        if attrs['coin']:
            asset = get_object_or_404(Asset, symbol=attrs['coin'])
        else:
            asset = None

        if not re.match(network.address_regex, address):
            raise ValidationError('آدرس به فرمت درستی وارد نشده است.')

        return {
            'account': account,
            'network': network,
            'asset': asset,
            'name': name,
            'address': address,
        }

    class Meta:
        model = AddressBook
        fields = ('name', 'account', 'network', 'asset', 'coin', 'address', 'deleted')


class AddressBookView(ModelViewSet):
    serializer_class = AddressBookSerializer

    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        query_params = self.request.query_params
        addressbook = AddressBook.objects.filter(deleted=False, account=self.request.user.account).order_by('-id')

        if 'coin' in query_params:
            addressbook = addressbook.filter(asset__symbol=query_params['coin'])

        if 'type' in query_params:
            if query_params['type'] == 'standard':
                addressbook = addressbook.filter(asset__isnull=False)
            elif query_params['type'] == 'universal':
                addressbook = addressbook.filter(asset__isnull=True)
            else:
                addressbook = addressbook

        return addressbook

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()

        return Response({'msg': 'address book deleted'}, status=status.HTTP_204_NO_CONTENT)
