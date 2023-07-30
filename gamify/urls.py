from django.urls import path
from gamify import views


urlpatterns = [
    path('missions/', views.UserMissionsAPIView.as_view(), ),
    path('missions/active/', views.ActiveUserMissionsAPIView.as_view(), ),
    path('voucher/', views.TotalVoucherAPIView.as_view(), ),
]
