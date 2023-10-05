from django.db import models

from accounts.models import User


class FeedBackCategory(models.Model):
    category = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.category

    class Meta:
        verbose_name = 'دسته‌بندی بازخورد برداشت'
        verbose_name_plural = 'دسته‌بندی‌های بازخورد برداشت'


class WithdrawFeedback(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    category = models.ForeignKey(FeedBackCategory, on_delete=models.PROTECT)
    description = models.TextField(blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'بازخورد برداشت'
        verbose_name_plural = 'بازخورد های برداشت'
