from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.authentication import CustomTokenAuthentication
from accounts.models import SmsNotification, User, Notification, EmailNotification
from gamify.models import UserMission

SMS, EMAIL, PUSH, MISSION = 'sms', 'email', 'push', 'mission'


class NotifyView(APIView):
    authentication_classes = [CustomTokenAuthentication]

    class NotifySerializer(serializers.Serializer):
        user_id = serializers.IntegerField()
        type = serializers.ChoiceField(
            choices=[
                (SMS, SMS),
                (PUSH, PUSH),
                (EMAIL, EMAIL),
                (MISSION, MISSION)
            ])
        content = serializers.CharField(required=False)
        content_html = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        link = serializers.CharField(required=False, allow_blank=True)
        hidden = serializers.BooleanField(required=False, default=True)
        group_id = serializers.UUIDField()
        mission_template_id = serializers.IntegerField(required=False, default=0)

        def validate(self, attrs):
            _type = attrs.get('content')
            if _type == SMS:
                if attrs.get('content', None) is None and not (attrs.get('content', None) and attrs.get('content', None)):
                    raise serializers.ValidationError('one of the content or (template, param) should has value')
            elif _type == PUSH:
                if attrs.get('content', None) is None or attrs.get('tittle', None) is None:
                    raise serializers.ValidationError('one of the content or (template, param) should has value')
            elif _type == EMAIL:
                if attrs.get('content_html', None) is None or attrs.get('content', None) is None:
                    raise serializers.ValidationError('content_html, content should has value')
            elif _type == MISSION:
                if not attrs.get('mission_template_id', None):
                    raise serializers.ValidationError('mission_template_id, mission_template_id should has value')
            return attrs

    def post(self, request):
        serializer = self.NotifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        if not request.user.has_perm('accounts.can_generate_notification'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        _type = data['type']

        recipient = User.objects.filter(id=data['user_id']).first()

        if not recipient:
            return Response(status=status.HTTP_204_NO_CONTENT)

        if _type == SMS:
            _, created = SmsNotification.objects.get_or_create(
                recipient=recipient,
                group_id=data['group_id'],
                defaults={
                    'content': data['content'],
                }
            )
        elif _type == PUSH:
            _, created = Notification.objects.get_or_create(
                recipient=recipient,
                group_id=data['group_id'],
                defaults={
                    'title': data.get('title', None),
                    'link': data.get('link', None),
                    'message': data.get('content', None),
                    'hidden': data.get('hidden', True),
                    'push_status': Notification.PUSH_WAITING,
                    'source': 'crm'
                }
            )

        elif _type == EMAIL:
            _, created = EmailNotification.objects.get_or_create(
                recipient=recipient,
                group_id=data['group_id'],
                defaults={
                    'title': data.get('title', None),
                    'content': data.get('content', None),
                    'content_html': data.get('content_html', None),
                }
            )
        elif _type == MISSION:
            _, created = UserMission.objects.get_or_create(
                user=recipient,
                mission_id=int(data['mission_template_id']),
            )
        else:
            raise NotImplementedError

        if created:
            return Response(status=status.HTTP_201_CREATED)
        else:
            return Response(status=status.HTTP_204_NO_CONTENT)
