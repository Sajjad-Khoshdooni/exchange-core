from django.db import models


class Attribution(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    tracker_code = models.CharField(max_length=16, blank=True)
    network_name = models.CharField(max_length=64, blank=True)
    campaign_name = models.CharField(max_length=64, blank=True)
    adgroup_name = models.CharField(max_length=64, blank=True)
    creative_name = models.CharField(max_length=64, blank=True)
    action_name = models.CharField(max_length=16, blank=True)
    reinstalled = models.BooleanField(default=False)
    gps_adid = models.CharField(max_length=64, blank=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=512, blank=True)
    tracker_user_id = models.CharField(max_length=64, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    installed_at = models.DateTimeField(null=True, blank=True)
    country = models.CharField(max_length=16, blank=True)
    city = models.CharField(max_length=16, blank=True)

    class Meta:
        unique_together = ('ip_address', 'user_agent', 'gps_adid', 'installed_at')
