from django.urls import path
from django.views.decorators.cache import cache_page

from multimedia.views import ImageCreateView, BannerListView, SectionsView, ArticleView, ArticleSearchView, \
    PinnedArticlesView, FileCreateView, LatestBlogPostsView

urlpatterns = [
    path('image/', ImageCreateView.as_view()),
    path('file/', FileCreateView.as_view()),
    path('banners/', BannerListView.as_view()),
    path('faq/sections/', SectionsView.as_view()),
    path('faq/articles/<str:slug>/', ArticleView.as_view()),
    path('faq/articles/', ArticleSearchView.as_view()),
    path('faq/sections/<slug:slug>/recom/', PinnedArticlesView.as_view()),

    path('blog/posts/latest/', cache_page(3600)(LatestBlogPostsView.as_view())),
]
