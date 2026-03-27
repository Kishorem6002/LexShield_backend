from django.urls import path
from .views import PostListCreateView, PostDetailView, MyPostsView, UserPostsView

urlpatterns = [
    path('',                      PostListCreateView.as_view()),
    path('my/',                   MyPostsView.as_view()),
    path('user/<str:username>/',  UserPostsView.as_view()),
    path('<int:pk>/',             PostDetailView.as_view()),
]
