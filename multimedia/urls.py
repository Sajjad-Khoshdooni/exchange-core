from django.urls import path

from multimedia.views import ImageCreateView, BannerListView, SectionsView, ArticleView, ArticleSearchView

urlpatterns = [
    path('image/', ImageCreateView.as_view()),
    path('banners/', BannerListView.as_view()),
    path('sections/', SectionsView.as_view()),
    path('article/<slug:str>-<id:uuid>', ArticleView.as_view()),
    path('article/', ArticleSearchView.as_view())
]
