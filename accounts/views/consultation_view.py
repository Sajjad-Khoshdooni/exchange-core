from rest_framework.generics import CreateAPIView
from rest_framework.serializers import ModelSerializer
from rest_framework.exceptions import ValidationError

from accounts.models import Consultation


class ConsultationSerializer(ModelSerializer):

    def validate(self, attrs):
        user = self.context['request'].user
        if user.is_consulted:
            raise ValidationError('کاربر قبلا مشاوره شده است.')
        attrs['consultee'] = user
        return attrs

    class Meta:
        model = Consultation
        fields = ('description',)
        extra_kwargs = {
            'description': {'write_only': True}
        }


class ConsultationView(CreateAPIView):
    serializer_class = ConsultationSerializer
