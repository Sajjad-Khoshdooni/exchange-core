from django.urls import path
from accounts import views


urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),

    path('signup/init/', views.InitiateSignupView.as_view()),
    path('signup/', views.SignupView.as_view()),

    path('otp/verify/', views.VerifyOTPView.as_view()),

    path('user/', views.UserDetailView.as_view()),

    path('forget/init/', views.InitiateForgetPasswordView.as_view()),
    path('forget/', views.ForgetPasswordView.as_view()),

    path('verify/basic/', views.BasicInfoVerificationViewSet.as_view({
        'get': 'retrieve',
        'put': 'update',
    })),

    path('verify/searchline/', views.VerifySearchLine.as_view()),
]
