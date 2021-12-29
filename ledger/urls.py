from django.urls import path
from ledger import views


urlpatterns = [
    path('v1/general/assets/', views.GeneralAssetInfoView.as_view()),
]
