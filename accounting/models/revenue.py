from django.db import models

from ledger.utils.fields import get_amount_field, get_group_id_field


class FiatTrade(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    fiat_amount = get_amount_field(validators=())
    usdt_amount = get_amount_field(validators=())
    trade = get_group_id_field()


# class GapRevenue(models.Model):
#     pass
