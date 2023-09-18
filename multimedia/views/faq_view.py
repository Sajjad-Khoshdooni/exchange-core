from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from django.contrib.postgres.search import SearchVector

from multimedia.models import Section, Article


class ArticleMiniSerializer(serializers.Serializer):
    class Meta:
        model = Article
        fields = ('title', 'slug', 'uuid',)


class ArticleSerializer(serializers.Serializer):
    class Meta:
        model = Article
        fields = ('title', 'content')


class SectionMiniSerializer(serializers.Serializer):
    class Meta:
        model = Section
        fields = ('title', 'slug',)


class SectionSerializer(serializers.Serializer):
    parent = SectionMiniSerializer()
    articles = serializers.SerializerMethodField()

    @staticmethod
    def get_articles(section: Section):
        return ArticleMiniSerializer(
            many=True,
            data=Article.objects.filter(parent_section=section)
        )

    class Meta:
        model = Section
        fields = ('icon', 'title', 'description', 'slug', 'parent', 'articles',)


class SectionsView(ListAPIView):
    class Meta:
        model = Section


class ArticleView(RetrieveAPIView):
    serializers = ArticleSerializer

    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get('slug', '')
        uuid = kwargs.get('id', '')

        instance = get_object_or_404(Article, uuid=uuid, slug=slug)

        serializer = self.get_serializer(instance)

        return Response(serializer.data)


class ArticleSearchView(ListAPIView):
    serializer_class = ArticleMiniSerializer(many=True)
    paginate_by = 10

    def get_queryset(self):
        search_parameter = self.request.data.get('search', '')
        return super().get_queryset().annotate(
            search=SearchVector('title', 'content'),
        ).filter(search=search_parameter)

    class Meta:
        model = Article
