import requests
from django.conf import settings


def blocklink_income_request(start, end):
    data = {
        'start': start,
        'end': end
    }
    url = settings.BLOCKLINK_BASE_URL + '/api/v1/tracker/revenue/'
    header = {
        'Authorization': settings.BLOCKLINK_TOKEN
    }
    return requests.get(url=url, data=data, headers=header, timeout=60).json()
