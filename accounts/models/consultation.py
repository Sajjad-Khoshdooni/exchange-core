from django.db import models
from accounts.models import User


class Consultation(models.Model):
    PENDING, DONE = 'pending', 'DONE'

    created = models.DateTimeField(auto_now_add=True)
    consultee = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='کاربر متقاضی مشاوره',
                                  related_name='consultee_consultations')
    consulter = models.ForeignKey(User, limit_choices_to={'is_staff': True}, on_delete=models.PROTECT,
                                  null=True, blank=True, verbose_name='مشاور',
                                  related_name='consulter_consultations')

    status = models.CharField(choices=[
            (PENDING, PENDING),
            (DONE, DONE)
        ],
        default=PENDING,
        max_length=15,
        verbose_name='وضعیت'
    )
    description = models.TextField(null=True, blank=True, verbose_name='توضیحات')

    class Meta:
        verbose_name = 'درخواستهای مشاوره'
