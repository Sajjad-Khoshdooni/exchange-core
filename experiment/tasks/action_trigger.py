import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone
from yekta_config.config import config

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
        varint__type=Variant.SMS_NOTIF,
        user__first_fiat_deposit_date=None,
        user__date_joined__range=[start_time, end_time]
    )

    for variant_user in variant_user_list:
        variant_data = variant_user.variant.data
        params = variant_data.get('params')
        params.update({
            'url': config('EXPERIMENT_DEPOSIT_URL')
        })
        sms = send_message_by_sms_ir(
            phone=variant_user.user.phone,
            template=variant_data.get('template_id'),
            params=variant_data.get('params')
        )
        if sms:
            variant_user.is_done = True
            variant_user.save(update_fields=['is_done'])
            logger.log('ExperimentSMSSentSuccessfully', extra={
                'variant_user': variant_user.id
            })
        else:
            logger.log('ExperimentSMSDoesntSent', extra={
                'variant_user': variant_user.id
            })
