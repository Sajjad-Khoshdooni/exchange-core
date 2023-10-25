from accounts.models import User, Company

from rest_framework import serializers
from rest_framework.generics import UpdateAPIView


class RegisterDocuments(CreateAPIView):
    def create(self, request, *args, **kwargs):
        pass

#what is the type of serializer field