from django.urls import path
from .views import ReportCreateView, ReportListView

urlpatterns = [
    path('',     ReportCreateView.as_view()),
    path('all/', ReportListView.as_view()),
]
