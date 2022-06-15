from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models.firebase_token import FirebaseToken


class FirebaseTokenSerializer(serializers.ModelSerializer):

    class Meta:
        model = FirebaseToken
        fields = ('token',)


class FirebaseTokenView(APIView):
    permission_classes = []

    def post(self, request):

        user = self.request.user
        if user.is_anonymous:
            user = None

        serializer = FirebaseTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = serializer.validated_data['token']

        firebase_token = FirebaseToken.objects.all()
        filter_firebase_token = firebase_token.filter(token=token)
        if filter_firebase_token:
            if user and filter_firebase_token.values_list('user', flat=True)[0] is None:
                filter_firebase_token.update(user=user)
                return Response({'msg': 'توکن اپدیت شد.'})
            else:
                return Response({'msg': 'امکان انتقال توکن به کاربر دیگر وجود ندارد.'})
        else:
            if user is None or not firebase_token.filter(user=user):
                FirebaseToken.objects.create(token=token, user=user)
                return Response({'msg': 'token create'})
            else:
                firebase_token.filter(user=user).update(token=token)
                return Response({'msg': 'token update'})
