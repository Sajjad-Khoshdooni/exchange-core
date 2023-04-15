from rest_framework.generics import RetrieveAPIView
from rest_framework.serializers import ModelSerializer

from accounts.models import AppStatus


class AppStatusSerializer(ModelSerializer):
    class Meta:
        model = AppStatus
        fields = ('latest_version', 'force_update_version')


class AppStatusView(RetrieveAPIView):
    serializer_class = AppStatusSerializer
    permission_classes = []

    def get_object(self):
        return AppStatus.get_active()
