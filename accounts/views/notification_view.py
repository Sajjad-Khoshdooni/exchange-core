from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.viewsets import ModelViewSet

from accounts.models.notification import Notification


class NotificationSerializer(serializers.ModelSerializer):

    def update(self, instance: Notification, validated_data):

        if 'read' in validated_data and instance.read and not validated_data['read']:
            raise ValidationError({
                'read': 'نمی‌توانید نوتیف خوانده شده را برگردانید.'
            })

        return super(NotificationSerializer, self).update(instance, validated_data)

    class Meta:
        model = Notification
        fields = ('id', 'created', 'message', 'level', 'read')
        read_only_fields = ('id', 'created', 'message', 'level')


class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    
    def get_queryset(self):

        try:
            limit = int(self.request.query_params.get('limit'))
        except:
            limit = 20

        return Notification.objects.filter(
            recipient=self.request.user
        )[:limit]
