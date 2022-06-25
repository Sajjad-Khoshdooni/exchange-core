from django.core.exceptions import ValidationError
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models.firebase_token import FirebaseToken


class FirebaseTokenSerializer(serializers.ModelSerializer):
    token = serializers.CharField()

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

        firebase_token = FirebaseToken.objects.filter(token=token).first()

        if firebase_token:
            if user and firebase_token.user is None:
                FirebaseToken.objects.filter(token=token).update(user=user)
                return Response({'msg': 'token updated'})
            else:
                return Response({'msg': 'change user of token impossible'})
        else:
            FirebaseToken.objects.create(token=token, user=user)
            return Response({'msg': 'token create'})
