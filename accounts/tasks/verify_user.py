from celery import shared_task
import logging
from accounts.models import User


logger = logging.getLogger(__name__)


@shared_task
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User

    if not user.national_code_verified:
        logger.info('verifying national_code')



