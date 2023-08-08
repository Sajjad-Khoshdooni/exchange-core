from rest_framework.views import APIView
from rest_framework import serializers
class AlertViewSerializer(serializers.ModelSerializer):
    class Meta:
        ...
class AlertView(APIView):
    ...
