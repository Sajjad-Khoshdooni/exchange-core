from django.urls import path

from multimedia.views import ImageCreateView

urlpatterns = [
    path('image/', ImageCreateView.as_view())
]
