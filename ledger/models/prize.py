from django.db import models
from accounts.models import User


class Prize(models.Model):

    LEVEL2_PRIZE = 1
    SIGN_UP_PRIZE = 1
    FIRST_TRADE_PRIZE = 1

    user = models.ForeignKey(to=User, on_delete=models.CASCADE)

