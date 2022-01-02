from rest_framework import serializers
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import RetrieveAPIView

from accounts.models import User


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('phone', 'email')


class UserDetailView(RetrieveAPIView):
    serializer_class = UserSerializer
    authentication_classes = [SessionAuthentication]

    def get_object(self):
        return self.request.user
