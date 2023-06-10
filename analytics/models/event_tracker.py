from django.db import models


class EventTracker(models.Model):
    created = models.DateField(auto_now_add=True)
    updated = models.DateField(auto_now=True)
    name = models.CharField(max_length=30)
    last_trade_id = models.IntegerField(default=0)
    last_otc_trade_id = models.IntegerField(default=0)
    last_transfer_id = models.IntegerField(default=0)
    last_fiat_withdraw_id = models.IntegerField(default=0)
    last_payment_id = models.IntegerField(default=0)
    last_user_id = models.IntegerField(default=0)
    last_login_id = models.IntegerField(default=0)
    last_prize_id = models.IntegerField(default=0)
    last_staking_id = models.IntegerField(default=0)
    last_traffic_source_id = models.IntegerField(default=0)
