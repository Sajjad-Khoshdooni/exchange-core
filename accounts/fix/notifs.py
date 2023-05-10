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

