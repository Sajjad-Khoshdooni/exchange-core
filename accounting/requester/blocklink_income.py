import requests
from decouple import config


def blocklink_income_request(start, end):
    data = {
        'start': start,
        'end': end
    }
    url = config('BLOCKLINK_BASE_URL', default='https://blocklink.raastin.com') + '/api/v1/tracker/revenue/'
    header = {
        'Authorization': config('BLOCKLINK_TOKEN')
    }
    return requests.get(url=url, data=data, headers=header, timeout=10).json()
