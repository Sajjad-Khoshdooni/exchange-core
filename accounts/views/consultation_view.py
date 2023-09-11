from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from accounts.models import Consultation


class ConsultationSerializer(ModelSerializer):

    def validate(self, attrs):
        user = self.context['request'].user
        if user.is_consulted:
            raise ValidationError('کاربر قبلا مشاوره شده است.')
        return attrs

    class Meta:
        model = Consultation
        fields = ('consultee', 'description',)
        extra_kwargs = {
            'consultee': {'write_only': True},
            'description': {'write_only': True}
        }


class ConsultationView(CreateAPIView):
    serializer_class = ConsultationSerializer
