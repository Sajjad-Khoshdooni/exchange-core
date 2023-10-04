from django.db import models


class FeedBackCategory(models.Model):
    category = models.CharField(max_length=128)


class WithdrawFeedback(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(FeedBackCategory, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
