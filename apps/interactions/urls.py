from django.urls import path
from .views import LikeToggleView, LikeStatusView, FollowToggleView

urlpatterns = [
    path('like/<int:post_id>/',        LikeToggleView.as_view()),
    path('like/<int:post_id>/status/', LikeStatusView.as_view()),
    path('follow/<int:user_id>/',      FollowToggleView.as_view()),
]
