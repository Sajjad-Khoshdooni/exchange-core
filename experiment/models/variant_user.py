from django.db import models


class VariantUser(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    variant = models.ForeignKey('experiment.Variant', on_delete=models.CASCADE, db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, db_index=True)
    link = models.ForeignKey('experiment.Link', on_delete=models.CASCADE)
    triggered = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = (
            ('user', 'variant'),
        )

    def __str__(self):
        return 'UserId:{user} ,VariantId:{variant}'.format(user=self.user.id, variant=self.variant.id)
