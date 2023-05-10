import uuid
from accounts.models import *
from ledger.models import *

users = User.objects.filter(id__in=AddressKey.objects.filter(deleted=True).values_list('account__user_id').distinct()).order_by('id')
group_id = uuid.uuid5(uuid.NAMESPACE_URL, 'address-changed')

for u in users:
    Notification.objects.get_or_create(
        recipient=u,
        group_id=group_id,
        defaults={
            'title': 'آدرس‌های واریز تغییر یافت',
            'message': 'لطفا برای واریز ارز دیجیتال، آدرس جدید بسازید و به آدرس‌های قبلی واریز نداشته باشید.',
            'link': 'https://raastin.com/ninja/raastin/post/595',
            'level': Notification.ERROR,
            'push_status': Notification.PUSH_WAITING
        }
    )


for u in users:
    Notification.objects.get_or_create(
        recipient=u,
        group_id=group_id,
        defaults={
            'title': 'آدرس‌های واریز تغییر یافت',
            'message': 'لطفا برای واریز ارز دیجیتال، آدرس جدید بسازید و به آدرس‌های قبلی واریز نداشته باشید.',
            'link': 'https://arzplus.net/announcement-deposit/',
            'level': Notification.ERROR,
            'push_status': Notification.PUSH_WAITING
        }
    )


assets = Asset.objects.filter(symbol__in='NWC, 1000ELON, DC, REV, RACA, BLOK, 1M-KISHU, 1M-BABYDOGE, 1M-PIT, 1M-QUACK, 1M-VINU, 1000STARL, 1M-AKITA, SAMO, TON'.replace(' ', '').split(','))
uids  = Wallet.objects.filter(asset__in=assets).values_list('account__user_id', flat=True).distinct()
users = User.objects.filter(id__in=uids)
group_id = uuid.uuid5(uuid.NAMESPACE_URL, '1-coins-problem')

for u in users:
    Notification.objects.get_or_create(
        recipient=u,
        group_id=group_id,
        defaults={
            'title': 'رفع مشکل اختلال در نمایش کوین ها',
            'message': 'ضمن تشکر از شکیبایی شما کاربران عزیز، مشکل اختلال در نمایش قیمت و معامله که برای برخی کوین ها به وجود آمده بود، رفع شد.',
            'level': Notification.INFO,
            'push_status': Notification.PUSH_WAITING
        }
    )
