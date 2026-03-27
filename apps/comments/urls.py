from django.urls import path
from .views import CommentListCreateView, CommentDetailView

urlpatterns = [
    path('',          CommentListCreateView.as_view()),
    path('<int:pk>/', CommentDetailView.as_view()),
]
