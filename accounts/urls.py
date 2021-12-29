from django.urls import path
from accounts import views


urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),

    path('signup/init/', views.InitiateSignupView.as_view()),
    path('signup/', views.SignupView.as_view()),

    path('verify/', views.VerifyOTPView.as_view()),

    path('user/', views.UserDetailView.as_view()),
]
