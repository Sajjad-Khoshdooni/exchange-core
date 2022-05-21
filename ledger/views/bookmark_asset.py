from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import serializers

from accounts.models import Account, User
from ledger.models import Asset


class BookmarkAssetSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField()
    action = serializers.CharField()

    def update(self, instance, validated_data):
        asset = get_object_or_404(Asset, symbol=validated_data.get('symbol'))
        action = validated_data.get('action')
        if action == 'add':
            instance.account.bookmark_asset.add(asset)
        if action == 'remove':
            instance.account.bookmark_asset.remove(asset)

        return instance

    class Meta:
        model = Account
        fields = ['bookmark_asset', 'symbol', 'action']



class BookmarkAssetAPIView(APIView):

    serializer = BookmarkAssetSerializer

    def patch(self, request):
        user = self.request.user
        book_mark_asset_serializer = BookmarkAssetSerializer(
            instance=user,
            data=request.data,
            partial=True
        )
        book_mark_asset_serializer.is_valid(raise_exception=True)
        book_mark_asset_serializer.save()
        return Response({'msg': 'ok'})

    def get_queryset(self):
        return User.objects.get(user=self.request.user)
