from django.contrib.auth import authenticate, login, logout
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


class LoginSerializer(serializers.Serializer):
    login = serializers.CharField(required=True)
    password = serializers.CharField(required=True)

    def save(self, **kwargs):
        login = self.validated_data['login']
        password = self.validated_data['password']
        return authenticate(login=login, password=password)


class LoginView(APIView):
    permission_classes = []

    def post(self, request):

        if request.user.is_authenticated:
            return Response({'msg': 'already logged in', 'code': 1, 'user_id': request.user.id})

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        if user:
            login(request, user)
            return Response({'msg': 'success', 'code': 0, 'user_id': user.id})
        else:
            return Response({'msg': 'authentication failed', 'code': -1}, status=status.HTTP_401_UNAUTHORIZED)


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response({'msg': 'success'})
