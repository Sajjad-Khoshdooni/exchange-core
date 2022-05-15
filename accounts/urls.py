from django.urls import path, include
from rest_framework import routers

from accounts import views
from accounts.views.user_view import CreateAuthToken

router = routers.DefaultRouter()

router.register(r'^referrals', views.ReferralViewSet, basename='referral')
urlpatterns = [
    path('login/', views.LoginView.as_view()),
    path('logout/', views.LogoutView.as_view()),

    path('signup/init/', views.InitiateSignupView.as_view()),
    path('signup/', views.SignupView.as_view()),

    path('otp/verify/', views.VerifyOTPView.as_view()),
    path('otp/send/', views.SendOTPView.as_view()),

    path('user/', views.UserDetailView.as_view()),

    path('forget/init/', views.InitiateForgetPasswordView.as_view()),
    path('forget/', views.ForgetPasswordView.as_view()),

    path('verify/basic/', views.BasicInfoVerificationViewSet.as_view({
        'get': 'retrieve',
        'post': 'update',
    })),

    path('verify/full/', views.FullVerificationViewSet.as_view({
        'get': 'retrieve',
        'post': 'update',
    })),

    path('verify/tel/init/', views.InitiateTelephoneVerifyView.as_view()),
    path('verify/tel/otp/', views.TelephoneOTPVerifyView.as_view()),

    path('verify/email/otp/', views.EmailVerifyView.as_view()),
    path('verify/email/verify/', views.EmailOTPVerifyView.as_view()),

    path('notifs/', views.NotificationViewSet.as_view({
        'get': 'list',
    })),

    path('notifs/<int:pk>/', views.NotificationViewSet.as_view({
        'get': 'retrieve',
        'patch': 'partial_update',
    })),

    path('notifs/all/', views.UnreadAllNotificationView.as_view()),
    path('password', views.ChangePasswordView.as_view()),

    path('quiz/passed/', views.QuizPassedView.as_view()),

    path('user/onboarding/', views.OnBoardingFlowStatus.as_view()),

    path('phone/change/', views.ChangePhoneView.as_view()),

    path('api/token/', CreateAuthToken.as_view()),

    path('referrals/overview/', views.ReferralOverviewAPIView.as_view()),
    path('referrals/report/', views.ReferralReportAPIView.as_view()),
    path('login/activity/', views.LoginActivityView.as_view()),
    path('fee/', views.TradingFeeView.as_view()),

    path('', include(router.urls)),
]
