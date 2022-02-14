from rest_framework import serializers
from rest_framework.viewsets import ModelViewSet

from accounts.models.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ('id', 'created', 'message', 'level', 'read')
        read_only_fields = ('id', 'created', 'message', 'level')


class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    
    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        )
