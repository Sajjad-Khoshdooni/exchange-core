from django.db import models


class Variant(models.Model):
    SMS_NOTIF = 'sms_notif'

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    name = models.CharField(max_length=20)
    type = models.CharField(choices=[(SMS_NOTIF, SMS_NOTIF)], max_length=30, blank=True)
    experiment = models.ForeignKey('experiment.Experiment', on_delete=models.CASCADE)
    data = models.JSONField(blank=True, null=True)

    def __str__(self):
        return 'Variant :{name}, {type}'.format(name=self.name, type=self.type)
