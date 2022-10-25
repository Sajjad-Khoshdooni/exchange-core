from rest_framework import serializers

from multimedia.models import Image


class ImageField(serializers.CharField):
    default_error_messages = {
        'not_found': 'عکس یافت نشد!'
    }

    def to_internal_value(self, data: dict):
        if type(data) is not dict:
            self.fail('not_found')

        uuid = data.get('uuid')
        try:
            return Image.objects.get(uuid=uuid)
        except Image.DoesNotExist:
            self.fail('not_found')

    def to_representation(self, value: Image):
        return {
            'uuid': value.uuid,
            'image': self.context['request'].build_absolute_uri(value.image.url),
        }
