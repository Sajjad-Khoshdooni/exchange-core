from django.db import models


class Experiment(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20)
    a_variant = models.ForeignKey('experiment.Variant', on_delete=models.CASCADE, null=True, blank=True, related_name='VARIANT_A')
    b_variant = models.ForeignKey('experiment.Variant', on_delete=models.CASCADE, related_name='VARIANT_B')
    active = models.BooleanField(default=True, db_index=True)
