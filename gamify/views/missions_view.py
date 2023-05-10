from django.db.models import Q
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from gamify.models import MissionJourney, Mission, Task, Achievement, UserMission
from ledger.models import Prize
from ledger.models.asset import AssetSerializerMini


class AchievementSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    asset = serializers.SerializerMethodField()
    achieved = serializers.SerializerMethodField()
    redeemed = serializers.SerializerMethodField()
    fake = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = ('id', 'amount', 'asset', 'achieved', 'redeemed', 'fake', 'voucher')

    def get_id(self, achievement: Achievement):
        prize = self.context['prize']
        return prize and prize.id

    def get_asset(self, achievement: Achievement):
        prize = self.context['prize']

        if prize:
            return prize.asset

        if not achievement.asset:
            return None

        return AssetSerializerMini(achievement.asset).data

    def get_amount(self, achievement: Achievement):
        prize = self.context['prize']

        if prize:
            return prize.amount
        else:
            return achievement.amount

    def get_achieved(self, achievement: Achievement):
        user = self.context['request'].user
        return achievement.achieved(user.get_account())

    def get_redeemed(self, achievement: Achievement):
        prize = self.context['prize']
        return bool(prize) and prize.redeemed

    def get_fake(self, achievement: Achievement):
        prize = self.context['prize']
        return bool(prize) and prize.fake


class TaskSerializer(serializers.ModelSerializer):
    progress = serializers.SerializerMethodField()
    finished = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ('scope', 'type', 'title', 'link', 'app_link', 'description', 'level', 'progress', 'finished')

    def get_progress(self, task: Task):
        user = self.context['request'].user
        return task.get_progress_percent(user.get_account())

    def get_finished(self, task: Task):
        user = self.context['request'].user
        return task.finished(user.get_account())


class MissionSerializer(serializers.ModelSerializer):
    achievements = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    finished = serializers.SerializerMethodField()
    active = serializers.SerializerMethodField()

    class Meta:
        model = Mission
        fields = ('name', 'achievements', 'tasks', 'active', 'finished', 'expiration')

    def get_achievements(self, mission: Mission):
        user = self.context['request'].user
        prize = Prize.objects.filter(account=user.get_account(), achievement=mission.achievement).first()

        context = {
            **self.context,
            'prize': prize
        }

        return [
            AchievementSerializer(mission.achievement, context=context).data,
        ]

    def get_tasks(self, mission: Mission):
        return TaskSerializer(mission.task_set.all(), many=True, context=self.context).data

    def get_finished(self, mission: Mission):
        user = self.context['request'].user
        return mission.finished(user.get_account())

    def get_active(self, mission: Mission):
        user = self.context['request'].user

        user_mission = UserMission.objects.filter(user=user, mission__active=True).first()

        if user_mission:
            return mission == user_mission

        return mission.journey.get_active_mission(user.get_account()) == mission

    @property
    def data(self):
        if self.instance is None:
            return {}
        else:
            return super(MissionSerializer, self).data


class MissionsAPIView(ListAPIView):
    serializer_class = MissionSerializer

    def get_queryset(self):
        account = self.request.user.get_account()
        journey = MissionJourney.get_journey(account)
        return Mission.objects.filter(Q(journey=journey) | Q(usermission__user=account.user), active=True)

    def list(self, request, *args, **kwargs):
        resp = super(MissionsAPIView, self).list(request, *args, **kwargs)
        data = resp.data

        data = list(filter(lambda d: d['active'], data)) + list(filter(lambda d: not d['active'], data))

        return Response(data)


class ActiveMissionsAPIView(RetrieveAPIView):
    serializer_class = MissionSerializer

    def get_object(self):
        account = self.request.user.get_account()
        journey = MissionJourney.get_journey(account)
        return journey and journey.get_active_mission(account)


class TotalVoucherAPIView(APIView):

    def get(self, request):
        account = self.request.user.get_account()
        voucher = account.get_voucher_wallet()

        voucher_amount = 0

        if voucher:
            voucher_amount = voucher.balance

        return Response({
            'voucher_usdt': voucher_amount
        })
