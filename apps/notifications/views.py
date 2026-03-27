from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from common.utils import success_response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        notifications = Notification.objects.filter(recipient=request.user)
        return success_response(NotificationSerializer(notifications, many=True).data)


class MarkAllReadView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return success_response(message='All notifications marked as read.')
