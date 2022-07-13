from django.db import models

from accounts.models import User


class FirebaseToken(models.Model):
    STATE_1 = '1'
    STATE_2 = '2'
    STATE_3 = '3'
    STATE_4 = '4'

    state_choice = ((STATE_1, 'token_between_2h_1d'), (STATE_2, 'Token_between_1d_7d'),
                    (STATE_3, 'token_more_than_7d'))

    created = models.DateTimeField(auto_now_add=True)

    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    token = models.CharField(max_length=256, unique=True)
    user_agent = models.TextField(blank=True)
    ip = models.GenericIPAddressField(null=True)
    state = models.CharField(max_length=1, choices=state_choice, default=STATE_1)

