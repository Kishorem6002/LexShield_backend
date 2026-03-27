from django.urls import path
from .views import UserAnalyticsView

urlpatterns = [
    path('me/', UserAnalyticsView.as_view()),
]
