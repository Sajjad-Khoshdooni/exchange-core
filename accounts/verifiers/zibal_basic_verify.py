import logging
from typing import Union

from accounts.models import User
from accounts.verifiers.zibal import ZibalRequester
from accounts.verifiers.jibit_basic_verify import send_shahkar_rejection_message

logger = logging.getLogger(__name__)


def shahkar_check(user: User, phone: str, national_code: str) -> Union[bool, None]:
    requester = ZibalRequester(user)
    resp = requester.matching(phone_number=phone, national_code=national_code)
    resp_data = resp.data
    if resp.success:
        is_matched = resp_data['data']['matched']
        if not is_matched:
            send_shahkar_rejection_message(user, resp)
        return is_matched
    else:
        logger.warning('Zibal shahkar not succeeded', extra={
            'user': user,
            'resp': resp_data,
            'phone': phone,
            'national_code': national_code
        })
        return
