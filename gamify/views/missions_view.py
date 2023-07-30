import django_filters
from django.db.models import QuerySet
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import serializers
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from gamify.models import Task, Achievement, UserMission
from ledger.models import Prize
from ledger.models.asset import AssetSerializerMini


class AchievementSerializer(serializers.ModelSerializer):
    id = serializers.SerializerMethodField()
    amount = serializers.SerializerMethodField()
    asset = serializers.SerializerMethodField()
    achieved = serializers.SerializerMethodField()
    redeemed = serializers.SerializerMethodField()
    fake = serializers.SerializerMethodField()
    type = serializers.SerializerMethodField()
    voucher = serializers.SerializerMethodField()
    voucher_expiration = serializers.SerializerMethodField()

    class Meta:
        model = Achievement
        fields = ('id', 'amount', 'asset', 'achieved', 'redeemed', 'fake', 'voucher', 'voucher_expiration', 'type')

    def get_id(self, achievement: Achievement):
        prize = self.context['prize']
        return prize and prize.id

    def get_type(self, achievement: Achievement):
        return achievement.type

    def get_asset(self, achievement: Achievement):
        prize = self.context['prize']

        if prize and (achievement.type == Achievement.NORMAL or prize.redeemed):
            return AssetSerializerMini(prize.asset).data

        if not achievement.asset:
            return None

        return AssetSerializerMini(achievement.asset).data

    def get_amount(self, achievement: Achievement):
        prize = self.context['prize']

        if prize and (achievement.type == Achievement.NORMAL or prize.redeemed):
            return prize.amount
        else:
            return achievement.amount

    def get_voucher(self, achievement: Achievement):
        prize = self.context['prize']

        if prize and (achievement.type == Achievement.NORMAL or prize.redeemed):
            return prize.voucher_expiration is not None
        elif achievement.type == Achievement.NORMAL:
            return achievement.voucher

    def get_voucher_expiration(self, achievement: Achievement):
        prize = self.context['prize']

        if prize and (achievement.type == Achievement.NORMAL or prize.redeemed):
            return prize.voucher_expiration

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


class UserMissionsFilter(django_filters.FilterSet):
    active = django_filters.BooleanFilter(method='custom_active_filter')

    def custom_active_filter(self, queryset, name, value):
        return queryset.filter(mission__active=value)

    class Meta:
        model = UserMission
        fields = ('active',)


class UserMissionSerializer(serializers.ModelSerializer):
    achievements = serializers.SerializerMethodField()
    tasks = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    expiration = serializers.SerializerMethodField()

    class Meta:
        model = UserMission
        fields = ('name', 'achievements', 'tasks', 'active', 'finished', 'expiration')

    def get_achievements(self, user_mission: UserMission):
        user = self.context['request'].user
        prize = Prize.objects.filter(account=user.get_account(), achievement=user_mission.mission.achievement).first()

        context = {
            **self.context,
            'prize': prize
        }

        return [
            AchievementSerializer(user_mission.mission.achievement, context=context).data,
        ]

    def get_tasks(self, user_mission: UserMission):
        return TaskSerializer(user_mission.mission.task_set.all(), many=True, context=self.context).data

    def get_name(self, user_mission: UserMission):
        return user_mission.mission.name

    def get_expiration(self, user_mission: UserMission):
        return user_mission.mission.expiration


class UserMissionsAPIView(ListAPIView):
    serializer_class = UserMissionSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_class = UserMissionsFilter

    def get_queryset(self):
        return UserMission.objects.filter(user=self.request.user)


class ActiveUserMissionsAPIView(RetrieveAPIView):
    serializer_class = UserMissionSerializer

    def get_object(self):
        account = self.request.user.get_account()
        for user_mission in UserMission.objects.filter(user=account.user):
            if user_mission.finished:
                return user_mission
        return QuerySet()


class TotalVoucherAPIView(APIView):
    # todo: remove this api

    def get(self, request):
        account = self.request.user.get_account()
        voucher = account.get_voucher_wallet()

        voucher_amount = 0

        if voucher:
            voucher_amount = voucher.balance

        return Response({
            'voucher_usdt': voucher_amount
        })
