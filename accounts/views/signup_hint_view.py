from rest_framework.response import Response
from rest_framework.generics import get_object_or_404
from rest_framework.views import APIView
from rest_framework import serializers

from accounts.models import User
from accounts.views.authentication import CustomTokenAuthentication


class SignUpHintSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class SignUpHintView(APIView):
    authentication_classes = [CustomTokenAuthentication]

    def get(self, request):
        serializer = SignUpHintSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = serializer.data.get('user_id')
        user = get_object_or_404(User, id=user_id)

        return Response({
            'first_name': user.first_name,
            'last_name': user.last_name
        }, 200)
