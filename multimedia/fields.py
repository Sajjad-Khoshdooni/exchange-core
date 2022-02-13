from rest_framework import serializers
from rest_framework.generics import get_object_or_404

from multimedia.models import Image


class ImageField(serializers.CharField):
    default_error_messages = {
        'not_found': 'عکس یافت نشد!'
    }

    def to_internal_value(self, data: str):
        try:
            return Image.objects.get(uuid=data)
        except Image.DoesNotExist:
            self.fail('not_found')

    def to_representation(self, value):
        return self.context['request'].build_absolute_uri(value.image.url)
