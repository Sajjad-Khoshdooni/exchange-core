from django.db import models


class ManualTransfer(models.Model):
    PROCESS, DONE = 'process', 'done'

    created = models.DateTimeField(auto_now_add=True)
    amount = models.PositiveIntegerField()
    reason = models.TextField(blank=True)
    bank_account = models.ForeignKey(
        'financial.BankAccount',
        on_delete=models.CASCADE,
        limit_choices_to={'stake_holder': True}
    )
    gateway = models.ForeignKey('financial.Gateway', on_delete=models.CASCADE)

    status = models.CharField(max_length=8, default=PROCESS, choices=((PROCESS, PROCESS), (DONE, DONE)))

    def __str__(self):
        return '%s IRT to %s' % (self.amount, self.bank_account)
