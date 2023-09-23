from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework import serializers
from rest_framework.parsers import FormParser, MultiPartParser, FileUploadParser

from accounts.authentication import is_app
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
    permission_classes = []

    def post(self, request, *args, **kwargs):
        return super(ImageCreateView, self).post(request, *args, **kwargs)


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ('id', 'title', 'image', 'link', 'app_link')


class BannerListView(ListAPIView):
    serializer_class = BannerSerializer
    permission_classes = []

    def get_queryset(self):
        banners = Banner.objects.filter(active=True)

        if is_app(self.request):
            banners = banners.exclude(limit=Banner.ONLY_DESKTOP)

        return banners
