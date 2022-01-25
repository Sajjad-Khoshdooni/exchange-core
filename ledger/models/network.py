from django.core.validators import MinValueValidator
from django.db import models
from rest_framework import serializers


class Network(models.Model):
    symbol = models.CharField(max_length=8, unique=True, db_index=True)

    can_withdraw = models.BooleanField(default=False)

    minimum_block_to_confirm = models.PositiveIntegerField(default=10, validators=[MinValueValidator(1)])

    def __str__(self):
        return self.symbol


class NetworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Network
        fields = ('symbol', )
