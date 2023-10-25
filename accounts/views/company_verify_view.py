from accounts.models import User, Company

from rest_framework import serializers
from rest_framework.generics import UpdateAPIView


class RegisterDocuments(UpdateAPIView):
    def create(self, request, *args, **kwargs):
        pass
