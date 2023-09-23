from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import serializers
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response

from django.contrib.postgres.search import TrigramWordSimilarity, SearchVector

from multimedia.models import Section, Article


class ArticleMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Article
        fields = ('id', 'title', 'slug',)


class ArticleSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()

    def get_content(self, article: Article):
        return article.content.html

    class Meta:
        model = Article
        fields = ('id', 'slug', 'title', 'content')


class SectionMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ('id', 'title', 'slug',)


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
        fields = ('id', 'icon', 'title', 'description', 'slug', 'parent', 'articles',)


class SectionsView(ListAPIView):
    serializer_class = SectionSerializer
    queryset = Section.objects.all()


class ArticleView(RetrieveAPIView):
    serializer_class = ArticleSerializer

    def get_object(self):
        kwargs = self.kwargs
        slug = kwargs.get('slug', '')
        print(slug)
        return get_object_or_404(Article, slug=slug)


class ArticleSearchView(ListAPIView):
    serializer_class = ArticleMiniSerializer
    queryset = Article.objects.all()
    paginate_by = 10

    def get_queryset(self):
        search_parameter = self.request.query_params.get('q', '')
        if not search_parameter:
            return Response({}, status=404)
        qs = super().get_queryset().annotate(
            search=SearchVector('title', 'title_en', 'content',)
        ).filter(search=search_parameter)
        return qs


class PinnedArticlesView(ListAPIView):
    serializer_class = ArticleMiniSerializer(many=True)
    paginate_by = 10

    def get_queryset(self):
        return super().get_queryset().filter(is_pinned=True)

    class Meta:
        model = Article
