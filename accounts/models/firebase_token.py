from django.db import models

from accounts.models import User


class FirebaseToken(models.Model):
    STATE_1 = '1'
    STATE_2 = '2'
    STATE_3 = '3'
    STATE_4 = '4'

    state_choice = ((STATE_1, '2h'), (STATE_2, '1d'),
                    (STATE_3, '7d'))

    created = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    token = models.CharField(max_length=256, unique=True)
    user_agent = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True)
    state = models.CharField(max_length=1, choices=state_choice, default=STATE_1)

