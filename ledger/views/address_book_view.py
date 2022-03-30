from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from ledger.models import AddressBook, Asset, Network


class address_book_serializer(serializers.ModelSerializer):

    asset = serializers.CharField(read_only=True)
    name = serializers.CharField()
    address = serializers.CharField()
    network = serializers.CharField()
    coin = serializers.CharField(write_only=True, required=False, default=None)

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
    serializer_class = address_book_serializer

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'address_book_list': serializer.data,
        })
    queryset = AddressBook.objects.all()

    def get_queryset(self):
        address_book = AddressBook.objects.filter(deleted=False, account=self.request.user.account)
        return address_book

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.deleted = True
        instance.save()

        return Response({'msg': 'address book deleted'})
