from django.db import models
from rest_framework import serializers


class Asset(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    symbol = models.CharField(max_length=8, unique=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)
    image = models.FileField(upload_to='asset-logo/')


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol', 'name', 'name_fa', 'image')


class AssetSerializerMini(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ('id', 'symbol')
