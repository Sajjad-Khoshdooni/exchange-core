from django.db import models
from accounts.models import User


class Account(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)

