from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.tasks import send_message_by_sms_ir
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser


@shared_task()
def trigger_variant_action():
    variant_user_list = VariantUser.objects.filter(
        is_done=False,
        varint__type=Variant.SMS_NOTIF,
        user__first_fiat_deposit_date=None,
        user__date_joined__range=[timezone.now()-timedelta(minutes=30), timezone.now()-timedelta(hours=2)]
    )

    for variant_user in variant_user_list:
        variant_data = variant_user.variant.data
        sms = send_message_by_sms_ir(
            phone=variant_user.user.phone,
            template=variant_data.get('template_id'),
            params=variant_data.get('params')
        )
        if sms:
            variant_user.is_done = True
            variant_user.save(update_fields=['is_done'])
