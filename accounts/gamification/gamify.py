import logging

from accounts.gamification.achievements import TradePrizeAchievementStep1, TradePrizeAchievementStep2, \
    VerifyPrizeAchievement
from accounts.gamification.goals import GoalGroup, VerifyLevel2Goal, DepositGoal, TradeStep1Goal, InviteGoal, \
    TradeStep2Goal, SetEmailGoal
from accounts.models import Account

logger = logging.getLogger(__name__)


goal_groups = [
    GoalGroup(
        conditions=[
            VerifyLevel2Goal
        ],
        achievements=[
            VerifyPrizeAchievement
        ]
    ),
    GoalGroup(
        conditions=[
            DepositGoal, TradeStep1Goal
        ],
        achievements=[
            TradePrizeAchievementStep1
        ]
    ),
    GoalGroup(
        conditions=[
            TradeStep2Goal, SetEmailGoal, InviteGoal
        ],
        achievements=[
            TradePrizeAchievementStep2
        ]
    )
]


def move_first(arr: list, index: int) -> list:
    if not index:
        return arr

    return arr[index: index + 1] + arr[:index] + arr[index + 1:]


def get_groups_data(account, only_active=False):
    groups = []

    activated = False
    active_index = None

    for i, group in enumerate(goal_groups):
        data = group.as_dict(account)

        if not list(filter(lambda achievement: achievement['fake'], data['achievements'])):
            data['active'] = not data['finished'] and not activated

            if data['active']:
                activated = True
                active_index = i

                if only_active:
                    return data

            groups.append(data)

    if only_active:
        return

    return move_first(groups, active_index)


def check_prize_achievements(account: Account):

    try:
        for group in goal_groups:
            if group.achievable(account):
                for achievement_cls in group.achievements:
                    achievement_cls(account).achieve_prize()

    except Exception as e:
        logger.exception('Failed to check prize achievements', extra={
            'account': account.id,
            'exp': e
        })
