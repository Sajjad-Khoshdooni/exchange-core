from rest_framework import serializers
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from accounts.authentication import CustomTokenAuthentication
from accounts.models import SmsNotification, User, Notification

SMS, EMAIL, PUSH = 'sms', 'email', 'push'


class NotifyView(APIView):
    authentication_classes = [CustomTokenAuthentication]

    class NotifySerializer(serializers.Serializer):
        user_id = serializers.IntegerField()
        type = serializers.ChoiceField(
            choices=[
                (SMS, SMS),
                (PUSH, PUSH),
                (EMAIL, EMAIL),
            ])
        content = serializers.CharField(required=False)
        template = serializers.CharField(required=False)
        param = serializers.CharField(required=False)
        title = serializers.CharField(required=False)
        link = serializers.CharField(required=False)
        hidden = serializers.BooleanField(required=False, default=True)
        group_id = serializers.UUIDField()

        def validate(self, attrs):
            _type = attrs.get('content')
            if _type == SMS:
                if attrs.get('content', None) is None and not (attrs.get('content', None) and attrs.get('content', None)):
                    return serializers.ValidationError('one of the content or (template, param) should has value')
            elif _type == PUSH:
                if attrs.get('content', None) is None or attrs.get('tittle', None) is None:
                    return serializers.ValidationError('one of the content or (template, param) should has value')
            return attrs

    def post(self, request):
        serializer = self.NotifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.data

        if not request.user.has_perm('accounts.can_generate_notification'):
            return Response(status=status.HTTP_403_FORBIDDEN)

        _type = data['type']

        if _type == SMS:
            SmsNotification.objects.create(
                recipient=User.objects.get(id=data['user_id']),
                template=data.get('template', None),
                params=data.get('params', None),
                content=data.get('content', None),
                group_id=data['group_id']
            )
        elif _type == PUSH:
            Notification.objects.create(
                recipient=User.objects.get(id=data['user_id']),
                title=data.get('content', None),
                link=data.get('content', None),
                message=data.get('content', None),
                hidden=data.get('group_id', True),
                push_status=Notification.PUSH_WAITING,
                group_id=data['group_id']
            )

        elif _type == EMAIL:
            pass

        return Response(status=status.HTTP_201_CREATED)
