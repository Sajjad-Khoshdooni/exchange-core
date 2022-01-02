from django.db import models
from rest_framework import serializers


class Network(models.Model):
    symbol = models.CharField(max_length=8, unique=True, db_index=True)
    name = models.CharField(max_length=64)
    name_fa = models.CharField(max_length=64)

    can_withdraw = models.BooleanField(default=False)

    def __str__(self):
        return self.symbol


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = '__all__'
