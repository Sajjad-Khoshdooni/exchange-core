import logging

from accounts.gamification.achievements import TradePrizeAchievementStep1, TradePrizeAchievementStep2
from accounts.gamification.goals import GoalGroup, VerifyLevel2Goal, DepositGoal, TradeStep1Goal, InviteGoal, \
    TradeStep2Goal
from accounts.models import Account

logger = logging.getLogger(__name__)


goal_groups = [
    GoalGroup(
        conditions=[
            VerifyLevel2Goal, DepositGoal, TradeStep1Goal
        ],
        achievements=[
            TradePrizeAchievementStep1
        ]
    ),
    GoalGroup(
        conditions=[
            InviteGoal, TradeStep2Goal
        ],
        achievements=[
            TradePrizeAchievementStep2
        ]
    )
]


def get_groups_data(account, only_active=False):
    groups = []

    activated = False

    for group in goal_groups:
        data = group.as_dict(account)

        data['active'] = not data['finished'] and not activated

        if data['active']:
            activated = True

            if only_active:
                return data

        groups.append(data)

    if only_active:
        return

    return groups


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
