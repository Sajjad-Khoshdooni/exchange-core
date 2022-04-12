from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers, status
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from ledger.models import AddressBook, Asset, Network
from rest_framework import filters


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

    def get_queryset(self):
        query_params = self.request.query_params
        addressbook = AddressBook.objects.filter(deleted=False, account=self.request.user.account)

        if 'coin' in query_params:
            addressbook = addressbook.filter(asset=get_object_or_404(Asset, symbol=query_params['coin']))

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

        return Response({'msg': 'address book deleted'},status=status.HTTP_204_NO_CONTENT)
