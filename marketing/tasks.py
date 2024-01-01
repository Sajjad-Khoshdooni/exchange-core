import time
from datetime import timedelta, datetime

import requests
from celery import shared_task
from decouple import config

from accounting.models import PeriodicFetcher
from accounting.models.periodic_fetcher import FetchError
from marketing.models import AdsReport, CampaignPublisherReport


def yektanet_requester(path: str, params: dict):
    url = 'https://api.yektanet.com/api/v1/external' + path
    header = {
        'Authorization': 'Token ' + config('YEKTANET_TOKEN')
    }
    resp = requests.get(url=url, params=params, headers=header, timeout=60)

    if not resp.ok:
        raise FetchError

    return resp.json()


UTM_TERM_PREFIX = {
    'native': 'yn_item_',
    'banner': 'yn_banner_',
    'mobile': 'yn_mob_',
}


def yektanet_ads_fetcher(start: datetime, end: datetime):
    # for ad_type in ('native', 'banner', 'push', 'mobile', 'video', 'universal'):
    for ad_type in ('native', 'banner', 'mobile'):
        resp = yektanet_requester('/campaigns-ad-report/', params={
            'type': ad_type,
            'start_date': str(start.date()),
            'end_date': str(end.date()),
        })

        for data in resp:
            AdsReport.objects.update_or_create(
                created=start,
                type=ad_type,
                utm_campaign=data['utm_campaign'],
                utm_term=UTM_TERM_PREFIX.get(ad_type, '') + str(data['ad_id']),
                ad_id=data['ad_id'],
                campaign_id=data['campaign_id'],
                defaults={
                    'views': data['views'],
                    'clicks': data['clicks'],
                    'cost': data['cost'],
                }
            )

        resp = yektanet_requester('/campaigns-publisher-report/', params={
            'type': ad_type,
            'start_date': str(start.date()),
            'end_date': str(end.date()),
        })

        for data in resp:
            CampaignPublisherReport.objects.update_or_create(
                created=start,
                type=ad_type,
                utm_campaign=data['utm_campaign'],
                utm_content=data['publisher_name'],
                campaign_id=data['campaign_id'],
                publisher_id=data['publisher_id'],
                defaults={
                    'views': data['views'],
                    'clicks': data['clicks'],
                    'cost': data['cost'],
                }
            )

        time.sleep(2)


@shared_task()
def fill_ads_reports():
    PeriodicFetcher.repetitive_fetch(
        name='marketing-yektanet-ads',
        fetcher=yektanet_ads_fetcher,
        interval=timedelta(days=1)
    )
