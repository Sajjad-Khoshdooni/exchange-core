import requests
from django.conf import settings


class AddressRequester:
    def create_wallet(self, account, architecture):
        data = {
            'architecture': architecture,
            'tag': '{brand}-base-{account_id}'.format(
                brand=settings.BRAND_EN.lower(),
                account_id=account.id,
            )
        }
        url = settings.BLOCKLINK_BASE_URL + '/api/v1/tracker/wallets/'
        header = {
            'Authorization': settings.BLOCKLINK_TOKEN
        }
        return requests.post(url=url, data=data, headers=header, timeout=10).json()
