from django.urls import path
from .views import (
    TextModerationView,
    ImageModerationView,
    VideoModerationView,
    AudioModerationView,
    MultimodalModerationView,
    ModerationLogListView,
)

urlpatterns = [
    path('text/',       TextModerationView.as_view()),
    path('image/',      ImageModerationView.as_view()),
    path('video/',      VideoModerationView.as_view()),
    path('audio/',      AudioModerationView.as_view()),
    path('multimodal/', MultimodalModerationView.as_view()),
    path('logs/',       ModerationLogListView.as_view()),
]
