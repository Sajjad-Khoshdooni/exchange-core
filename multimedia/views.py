from rest_framework.generics import CreateAPIView
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser

from multimedia.models import Image


class ImageSerializer(serializers.ModelSerializer):
    def validate(self, attrs):
        return attrs

    class Meta:
        model = Image
        fields = ('uuid', 'image')
        read_only_fields = ('uuid', )


class ImageCreateView(CreateAPIView):
    parser_classes = (FormParser, MultiPartParser, FileUploadParser)
    serializer_class = ImageSerializer
    queryset = Image.objects.all()

    def post(self, request, *args, **kwargs):
        return super(ImageCreateView, self).post(request, *args, **kwargs)