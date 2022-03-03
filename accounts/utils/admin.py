from django.conf import settings
from django.urls import reverse


def url_to_edit_object(obj):
    return settings.HOST_URL + reverse('admin:%s_%s_change' % (obj._meta.app_label,  obj._meta.model_name),  args=[obj.id] )
