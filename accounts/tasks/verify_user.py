import logging

from celery import shared_task

from accounts.models import User
from accounts.verifiers.basic_verify import basic_verify

logger = logging.getLogger(__name__)


@shared_task
def basic_verify_user(user_id: int):
    user = User.objects.get(id=user_id)  # type: User

    try:
        basic_verify(user)
    except:
        user.refresh_from_db()
        if user.verify_status == User.PENDING:
            user.change_status(User.REJECTED)

        raise
