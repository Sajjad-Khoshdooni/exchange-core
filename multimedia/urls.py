from django.urls import path

from multimedia.views import ImageCreateView, BannerListView, SectionsView, ArticleView, ArticleSearchView, \
    PinnedArticlesView, FileCreateView

urlpatterns = [
    path('image/', ImageCreateView.as_view()),
    path('file/', FileCreateView.as_view()),
    path('banners/', BannerListView.as_view()),
    path('faq/sections/', SectionsView.as_view()),
    path('faq/articles/<str:slug>/', ArticleView.as_view()),
    path('faq/articles/', ArticleSearchView.as_view()),
    path('faq/sections/<int:pk>/recom/', PinnedArticlesView.as_view()),
]
