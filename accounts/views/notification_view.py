from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from accounts.models.notification import Notification
from accounts.utils import parse_positive_int


class NotificationSerializer(serializers.ModelSerializer):

    def update(self, instance: Notification, validated_data):

        if 'read' in validated_data and instance.read and not validated_data['read']:
            raise ValidationError({
                'read': 'نمی‌توانید نوتیف خوانده شده را برگردانید.'
            })

        return super(NotificationSerializer, self).update(instance, validated_data)

    class Meta:
        model = Notification
        fields = ('id', 'created', 'title', 'message', 'level', 'read')
        read_only_fields = ('id', 'created', 'title', 'message', 'level')


class NotificationViewSet(ModelViewSet):
    serializer_class = NotificationSerializer
    
    def get_object(self):
        super(NotificationViewSet, self).get_object()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'notifications': serializer.data,
            'unread_count': Notification.objects.filter(recipient=self.request.user, read=False).count()
        })

    def get_queryset(self):
        query_params = self.request.query_params

        limit = parse_positive_int(query_params.get('limit'), default=20)
        offset = parse_positive_int(query_params.get('offset'), default=0)

        notifications = Notification.objects.filter(
            recipient=self.request.user
        )

        notifications = notifications[offset:limit]

        return notifications


class UnreadAllNotificationView(APIView):
    def patch(self, request):
        read = request.data.get('read')

        if read != True:
            raise ValidationError({'read': 'should be true!'})

        Notification.objects.filter(recipient=request.user).update(read=True)

        return Response('ok')
