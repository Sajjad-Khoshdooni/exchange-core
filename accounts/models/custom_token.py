from rest_framework.authtoken.models import Token
from django.contrib.postgres.fields import ArrayField
from django.db import models


class CustomToken(Token):
    ip_list = ArrayField(
            models.GenericIPAddressField(default='127.0.0.1'), default=list
    )
