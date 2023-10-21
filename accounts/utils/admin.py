from urllib.parse import urlencode

from django.conf import settings
from django.urls import reverse


def url_to_edit_object(obj):
    return settings.HOST_URL + reverse('admin:%s_%s_change' % (obj._meta.app_label,  obj._meta.model_name),  args=[obj.id] )


def url_to_admin_list(obj, filters: dict = None):
    url = settings.HOST_URL + reverse('admin:%s_%s_changelist' % (obj._meta.app_label,  obj._meta.model_name))

    if filters:
        url += '?' + urlencode(filters)

    return url
