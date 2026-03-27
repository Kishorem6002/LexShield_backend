from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .token import EmailTokenObtainPairView
from .views import RegisterView, MeView, LogoutView, AdminLoginView

urlpatterns = [
    path('register/',     RegisterView.as_view()),
    path('login/',        EmailTokenObtainPairView.as_view()),
    path('admin-login/',  AdminLoginView.as_view()),
    path('refresh/',      TokenRefreshView.as_view()),
    path('logout/',       LogoutView.as_view()),
    path('me/',           MeView.as_view()),
]
