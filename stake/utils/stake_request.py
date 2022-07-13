from django.core.exceptions import ValidationError


def change_status(old_status: str, new_status: str):

    from stake.models import StakeRequest

    mapping = {
        StakeRequest.PROCESS: 0,
        StakeRequest.PENDING: 1,
        StakeRequest.DONE: 2,
        StakeRequest.CANCEL_PROCESS: 3,
        StakeRequest.CANCEL_PENDING: 4,
        StakeRequest.CANCEL_COMPLETE: 5,
    }
    old_state_number = mapping[old_status]
    new_state_number = mapping[new_status]

    if new_state_number < old_state_number:
        raise ValidationError('امکان انجام تغییر وضعیت وجود ندارد.')
    if new_state_number == 5 and old_state_number == 0:
        return new_status
    elif new_state_number == 3 and old_state_number == 1:
        return StakeRequest.CANCEL_PROCESS
    elif (new_state_number - old_state_number) > 1:
        raise ValidationError('امکان انجام تغییر وضعیت وجود ندارد.')
    else:
        return new_status
