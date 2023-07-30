import logging

from django.db import transaction
from django.db.models import Q

from accounts.models import Account
from gamify.models import MissionJourney, Task, MissionTemplate, UserMission

__all__ = ('Task', 'check_prize_achievements')

logger = logging.getLogger(__name__)


def check_prize_achievements(account: Account, task_scope: str):
    scopes = [task_scope]

    if task_scope == Task.TRADE:
        scopes.append(Task.WEEKLY_TRADE)

    try:
        journey = MissionJourney.get_journey(account)

        user_missions = UserMission.objects.filter(
            Q(mission__journey=journey) | Q(user=account.user),
            mission__task__scope__in=scopes,
            mission__active=True,
            finished=False
        )

        for user_mission in user_missions:
            if user_mission.mission.achievable(account):
                with transaction.atomic():
                    user_mission.mission.achievement.achieve_prize(account)
                    user_mission.finished = True
                    user_mission.save(update_fields=['finished'])

    except Exception as e:
        logger.exception('Failed to check prize achievements', extra={
            'account': account.id,
            'exp': e
        })


def clone_model(instance):
    instance.pk = None
    instance.save()
    return instance


def clone_mission_template(mission: MissionTemplate):
    with transaction.atomic():
        tasks = list(mission.task_set.all())
        achievement = mission.achievement

        mission.name = mission.name + ' cloned'
        new_mission = clone_model(mission)

        achievement.mission = new_mission
        clone_model(achievement)

        for task in tasks:
            task.mission = new_mission
            clone_model(task)

    return new_mission
