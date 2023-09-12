from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ModelSerializer

from accounts.models import Consultation


class ConsultationSerializer(ModelSerializer):

    class Meta:
        model = Consultation
        fields = ('description',)
        extra_kwargs = {
            'description': {'write_only': True}
        }


class ConsultationView(CreateAPIView):
    serializer_class = ConsultationSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
