from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from django.contrib.postgres.search import SearchVector

from multimedia.models import Section, Article


class ArticleMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('title', 'slug', 'uuid',)


class ArticleSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    def get_content(self, article: Article):
        return article.content.html

    class Meta:
        model = Article
        fields = ('title', 'content')


class SectionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ('title', 'slug',)


class SectionSerializer(serializers.ModelSerializer):
    parent = SectionMiniSerializer()
    icon = serializers.ImageField()
    articles = serializers.SerializerMethodField()

    def get_articles(self, section: Section):
        queryset = Article.objects.filter(parent_section=section)
        serializer = ArticleMiniSerializer(queryset, many=True)
        return serializer.data

    class Meta:
        model = Section
        fields = ('icon', 'title', 'description', 'slug', 'parent', 'articles',)


class SectionsView(ListAPIView):
    serializer_class = SectionSerializer
    queryset = Section.objects.all()


class ArticleView(RetrieveAPIView):
    serializer_class = ArticleSerializer

    def retrieve(self, request, *args, **kwargs):
        slug = kwargs.get('slug', '')
        uuid = kwargs.get('uuid', '')

        instance = get_object_or_404(Article, uuid=uuid, slug=slug)

        serializer = self.get_serializer(instance=instance)

        return Response(serializer.data)


class ArticleSearchView(ListAPIView):
    serializer_class = ArticleMiniSerializer
    queryset = Article.objects.all()
    paginate_by = 10

    def get_queryset(self):
        search_parameter = self.request.query_params.get('search', '')
        return super().get_queryset().annotate(
            search=SearchVector('title', 'content'),
        ).filter(search=search_parameter)


class PinnedArticlesView(ListAPIView):
    serializer_class = ArticleMiniSerializer(many=True)
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(is_pinned=True)

    class Meta:
        model = Article
