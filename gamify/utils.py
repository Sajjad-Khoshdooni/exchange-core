from accounts.models import Account
from gamify.models import MissionJourney, Task

__all__ = ('Task', 'check_prize_achievements')


def check_prize_achievements(account: Account, task_scope: str):
    MissionJourney.get_journey(account).achieve_if_can(account, task_scope)
