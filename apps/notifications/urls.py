from django.urls import path
from .views import NotificationListView, MarkAllReadView

urlpatterns = [
    path('',          NotificationListView.as_view()),
    path('read-all/', MarkAllReadView.as_view()),
]
