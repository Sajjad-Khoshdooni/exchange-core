from django.contrib.auth import authenticate, login
from rest_framework import serializers, status
from rest_framework.generics import CreateAPIView
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
    serializer_class = LoginSerializer

    def post(self, request):

        # if request.user.is_authenticated:
        #     return Response({'msg': 'already logged in'})

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.save()

        if user:
            login(request, user)
            return Response({'msg': 'success'})
        else:
            return Response({'msg': 'authentication failed'}, status=status.HTTP_401_UNAUTHORIZED)
