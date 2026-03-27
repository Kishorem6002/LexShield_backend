from django.urls import path
from .views import MyProfileView, UserProfileView

urlpatterns = [
    path('me/',                MyProfileView.as_view()),
    path('user/<str:username>/', UserProfileView.as_view()),
]
