import json
import requests
from django.conf import settings
from decouple import config
from decouple import config


class AddressRequester:
    def create_wallet(self, account, architecture):
        data = {
            'architecture': architecture,
            'tag': '{brand}-base-{account_id}'.format(
                brand=settings.BRAND_EN.lower(),
                account_id=account.id,
            )
        }
        url = config('BLOCKLINK_BASE_URL', default='https://blocklink.raastin.com') + '/api/v1/tracker/wallets/'
        header = {
            'Authorization': config('BLOCKLINK_TOKEN')
        }
        return requests.post(url=url, data=data, headers=header, timeout=10).json()
