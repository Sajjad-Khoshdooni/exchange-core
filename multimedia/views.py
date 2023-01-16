from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser

from multimedia.models import Image, Banner


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


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'title', 'image', 'link', 'app_link')


class BannerListView(ListAPIView):
    authentication_classes = []
    permission_classes = []
    serializer_class = BannerSerializer
    queryset = Banner.objects.filter(active=True)
