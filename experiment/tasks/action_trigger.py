import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from accounts.tasks import send_message_by_sms_ir
from experiment.models.variant import Variant
from experiment.models.variant_user import VariantUser

logger = logging.getLogger(__name__)


@shared_task()
def trigger_variant_action():
    now = timezone.now()
    start_time, end_time = now - timedelta(hours=2), now - timedelta(minutes=30)
    variant_user_list = VariantUser.objects.filter(
        triggered=False,
        variant__type=Variant.SMS_NOTIF,
        user__first_fiat_deposit_date=None,
        user__date_joined__range=[start_time, end_time]
    )

    for variant_user in variant_user_list:
        variant_data = variant_user.variant.data
        raw_params = variant_data.get('params')

        url = variant_user.link.get_sms_link()
        template_id = variant_data['template_id']
        params = {k: v.replace('%url%', url) for (k, v) in raw_params.items()}

        sms = send_message_by_sms_ir(
            phone=variant_user.user.phone,
            template=template_id,
            params=params
        )
        if sms:
            variant_user.triggered = True
            variant_user.save(update_fields=['triggered'])
            logger.info('experiment sms successful variant=%s' % variant_user.id)
        else:
            logger.info('experiment sms failed variant=%s' % variant_user.id)