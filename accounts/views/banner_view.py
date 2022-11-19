from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from gamify.models import MissionJourney, Task
from ledger.models import Prize


class TaskSerializer(serializers.ModelSerializer):
    text = serializers.CharField(source='description')
    btn_link = serializers.CharField(source='link')
    btn_title = serializers.CharField(source='title')

    class Meta:
        model = Task
        fields = ('text', 'btn_link', 'btn_title', 'level')


class BannerAlertAPIView(APIView):
    def get(self, request):

        # return Response({
        #     'banner': {
        #         'text': 'کاربران گرامی، با عرض پوزش به اطلاع می رساند که سیستم در حال به روز رسانی است. لذا ممکن است تا دقایقی در مشاهده موجودی ها و برخی بخش های دیگر اختلالاتی مشاهده شود.',
        #         'btn_link': '/fdsfds',
        #         'btn_title': '',
        #         'level': 'warning'
        #     }
        # })

        return Response({
            'banner': self.get_alert_condition()
        })

    def get_alert_condition(self):
        account = self.request.user.account
        task = None

        if Prize.objects.filter(account=account, fake=False, redeemed=False).exists():
            task = Task(
                scope='redeem_prize',
                title='دریافت جایزه',
                type=Task.BOOL,
                link='/account/tasks',
                description='جایزه‌ای به شما تعلق گرفت. برای دریافت آن کلیک کنید.',
            )

        try:
            task = MissionJourney.get_journey(account).get_active_mission(account).get_active_task(account)
        except AttributeError:
            pass

        if task:
            return TaskSerializer(task).data
