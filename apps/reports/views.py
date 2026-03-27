from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from common.utils import success_response, created_response, error_response
from common.permissions import IsAdminOrModerator
from common.pagination import StandardPagination
from .models import Report
from .serializers import ReportSerializer


def _notify_reported_user(report, reporter_username):
    """Notify the owner of the reported content."""
    try:
        from services.notifications.notification_service import send_notification
        from django.contrib.auth import get_user_model
        User = get_user_model()

        content_type = report.content_type
        object_id    = report.object_id
        recipient_id = None

        if content_type == 'post':
            from apps.posts.models import Post
            obj = Post.all_objects.filter(id=object_id).first()
            if obj: recipient_id = obj.user_id

        elif content_type == 'comment':
            from apps.comments.models import Comment
            obj = Comment.all_objects.filter(id=object_id).first()
            if obj: recipient_id = obj.user_id

        elif content_type == 'profile':
            recipient_id = object_id

        if recipient_id and recipient_id != report.reported_by_id:
            send_notification(
                recipient_id,
                f"Your {content_type} has been reported for review.",
                {
                    'type':         'report',
                    'content_type': content_type,
                    'object_id':    object_id,
                    'reason':       report.reason[:100],
                }
            )
    except Exception:
        pass


class ReportCreateView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        serializer = ReportSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(errors=serializer.errors)

        report = serializer.save(reported_by=request.user)

        # Notify the reported user
        _notify_reported_user(report, request.user.username)

        return created_response(serializer.data, message='Report submitted.')


class ReportListView(APIView):
    permission_classes = (IsAdminOrModerator,)

    def get(self, request):
        reports   = Report.objects.filter(status='PENDING')
        paginator = StandardPagination()
        page      = paginator.paginate_queryset(reports, request)
        return paginator.get_paginated_response(ReportSerializer(page, many=True).data)
