import re

from django.shortcuts import get_object_or_404
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from ledger.models import AddressBook, Asset, Network, NetworkAsset
from ledger.models.asset import AssetSerializerMini
from ledger.views.network_asset_info_view import NetworkAssetSerializer


class AddressBookSerializer(serializers.ModelSerializer):
    account = serializers.CharField(read_only=True)
    asset = AssetSerializerMini(read_only=True)
    network = serializers.CharField()
    coin = serializers.CharField(write_only=True, required=False, default=None)
    deleted = serializers.BooleanField(read_only=True)
    network_info = serializers.SerializerMethodField()

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

    def get_network_info(self, address_book: AddressBook):
        coin = self.context.get('coin')

        if coin:
            network_asset = get_object_or_404(NetworkAsset, asset__symbol=coin, network=address_book.network)

            return NetworkAssetSerializer(network_asset).data

    class Meta:
        model = AddressBook
        fields = ('id', 'name', 'account', 'network', 'asset', 'coin', 'address', 'deleted', 'network_info')


class AddressBookView(ModelViewSet):
    serializer_class = AddressBookSerializer

    pagination_class = LimitOffsetPagination

    def get_queryset(self):
        query_params = self.request.query_params
        address_books = AddressBook.objects.filter(deleted=False, account=self.request.user.account).order_by('-id')

        if 'coin' in query_params:
            address_books = address_books.filter(asset__symbol=query_params['coin'])

        if 'type' in query_params:
            if query_params['type'] == 'standard':
                address_books = address_books.filter(asset__isnull=False)
            elif query_params['type'] == 'universal':
                address_books = address_books.filter(asset__isnull=True)
            else:
                address_books = address_books

        return address_books

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()

        return Response({'msg': 'address book deleted'}, status=status.HTTP_204_NO_CONTENT)

    def get_serializer_context(self):
        return {
            **super(AddressBookView, self).get_serializer_context(),
            'coin': self.request.query_params.get('coin'),
        }
