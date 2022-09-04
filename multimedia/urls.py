from django.urls import path

from multimedia.views import ImageCreateView, BannerListView

urlpatterns = [
    path('image/', ImageCreateView.as_view()),
    path('banners/', BannerListView.as_view()),
]
