from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Avg
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta

from common.permissions import IsAdmin
from common.pagination import StandardPagination
from common.utils import success_response, error_response
from apps.accounts.models import User
from apps.posts.models import Post
from apps.comments.models import Comment
from apps.moderation.models import ModerationLog
from apps.reports.models import Report


def _parse_date_range(request):
    days = int(request.query_params.get('days', 30))
    days = min(max(days, 1), 365)
    return timezone.now() - timedelta(days=days)


VIOLATION_KEYWORDS = {
    'Harassment':      ['harass', 'bully', 'threat', 'intimidat'],
    'Hate Speech':     ['hate', 'racist', 'discriminat', 'slur'],
    'Nudity':          ['nudity', 'nude', 'explicit', 'nsfw'],
    'Violence':        ['violen', 'gore', 'blood', 'weapon', 'kill'],
    'Sexual Content':  ['sexual', 'porn', 'erotic', 'adult content'],
    'Spam':            ['spam', 'scam', 'phish', 'fake', 'mislead'],
}


def _sensitive_analysis(mod_logs):
    result = {cat: 0 for cat in VIOLATION_KEYWORDS}
    for log in mod_logs.exclude(status='APPROVED').only('reason'):
        reason = log.reason.lower()
        for cat, keywords in VIOLATION_KEYWORDS.items():
            if any(kw in reason for kw in keywords):
                result[cat] += 1
    return result


class AdminDashboardMetricsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        since = _parse_date_range(request)
        now   = timezone.now()

        # ── Overview ─────────────────────────────────────────────────────
        total_users    = User.objects.count()
        total_posts    = Post.all_objects.count()
        total_comments = Comment.all_objects.count()
        total_uploads  = total_posts + total_comments

        mod_logs       = ModerationLog.objects.all()
        approved_count = mod_logs.filter(status='APPROVED').count()
        flagged_count  = mod_logs.filter(status='FLAGGED').count()
        blocked_count  = mod_logs.filter(status='BLOCKED').count()

        pending_reports  = Report.objects.filter(status='PENDING')
        total_reports    = Report.objects.count()
        pending_reviews  = pending_reports.count()

        # ── Sensitive content ─────────────────────────────────────────────
        sensitive_analysis = _sensitive_analysis(mod_logs)

        # ── Recent uploads ────────────────────────────────────────────────
        recent_logs = (
            mod_logs
            .select_related('requested_by')
            .order_by('-created_at')[:20]
        )
        recent_uploads = [
            {
                'id':               log.id,
                'username':         log.requested_by.username if log.requested_by else 'Anonymous',
                'content_type':     log.content_type or 'direct',
                'modality':         log.modality,
                'status':           log.status,
                'detected_labels':  log.reason[:120] if log.reason else '',
                'confidence_score': round(float(log.confidence), 1),
                'severity':         log.severity,
                'escalated':        log.escalated,
                'timestamp':        log.created_at,
            }
            for log in recent_logs
        ]

        # ── Reports analytics ─────────────────────────────────────────────
        reports_by_type   = list(Report.objects.values('content_type').annotate(count=Count('id')))
        reports_by_status = list(Report.objects.values('status').annotate(count=Count('id')))

        # ── High-risk users (fixed annotation) ───────────────────────────
        high_risk_qs = (
            User.objects
            .annotate(
                post_count_val    = Count('posts',               distinct=True),
                comment_count_val = Count('comments',            distinct=True),
                flagged_count     = Count('moderation_requests',
                                         filter=Q(moderation_requests__status='FLAGGED'),
                                         distinct=True),
                blocked_count     = Count('moderation_requests',
                                         filter=Q(moderation_requests__status='BLOCKED'),
                                         distinct=True),
                reports_received  = Count('reports_filed',       distinct=True),
            )
            .filter(Q(flagged_count__gt=0) | Q(blocked_count__gt=0))
            .order_by('-blocked_count', '-flagged_count')[:10]
        )
        high_risk_data = [
            {
                'username':        u.username,
                'email':           u.email,
                'total_uploads':   u.post_count_val + u.comment_count_val,
                'flagged_count':   u.flagged_count,
                'blocked_count':   u.blocked_count,
                'reports_received':u.reports_received,
                'risk_score':      (u.flagged_count * 2) + (u.blocked_count * 5) + (u.reports_received * 3),
                'is_active':       u.is_active,
            }
            for u in high_risk_qs
        ]

        # ── Pending review summary ────────────────────────────────────────
        oldest_pending = pending_reports.order_by('created_at').first()

        # ── Trend analysis ────────────────────────────────────────────────
        mod_trends = list(
            mod_logs.filter(created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(
                total   = Count('id'),
                flagged = Count('id', filter=Q(status='FLAGGED')),
                blocked = Count('id', filter=Q(status='BLOCKED')),
            )
            .order_by('date')
        )
        report_trends = list(
            Report.objects.filter(created_at__gte=since)
            .annotate(date=TruncDate('created_at'))
            .values('date')
            .annotate(total=Count('id'))
            .order_by('date')
        )
        all_dates = sorted(
            set([t['date'] for t in mod_trends] + [r['date'] for r in report_trends])
        )
        trends_data = []
        for d in all_dates:
            t = next((x for x in mod_trends    if x['date'] == d), {})
            r = next((x for x in report_trends if x['date'] == d), {})
            trends_data.append({
                'date':    str(d),
                'uploads': t.get('total',   0),
                'flagged': t.get('flagged', 0),
                'blocked': t.get('blocked', 0),
                'reports': r.get('total',   0),
            })

        # ── Modality breakdown ────────────────────────────────────────────
        modality_breakdown = list(
            mod_logs.values('modality')
            .annotate(
                total          = Count('id'),
                flagged        = Count('id', filter=Q(status='FLAGGED')),
                blocked        = Count('id', filter=Q(status='BLOCKED')),
                avg_confidence = Avg('confidence'),
            )
            .order_by('modality')
        )

        return Response({
            'overview_metrics': {
                'total_users':       total_users,
                'total_uploads':     total_uploads,
                'approved_uploads':  approved_count,
                'flagged_uploads':   flagged_count,
                'blocked_uploads':   blocked_count,
                'pending_reviews':   pending_reviews,
                'total_reports':     total_reports,
            },
            'moderation_status_distribution': {
                'APPROVED':     approved_count,
                'FLAGGED':      flagged_count,
                'BLOCKED':      blocked_count,
                'UNDER_REVIEW': pending_reviews,
            },
            'modality_breakdown':       modality_breakdown,
            'sensitive_content_analysis': sensitive_analysis,
            'recent_uploads':           recent_uploads,
            'reports_analytics': {
                'total_reports': total_reports,
                'by_type':       reports_by_type,
                'by_status':     reports_by_status,
            },
            'high_risk_users': high_risk_data,
            'pending_review_summary': {
                'total_pending':  pending_reviews,
                'oldest_pending': oldest_pending.created_at if oldest_pending else None,
            },
            'trends': trends_data,
        })


class AdminUsersListView(APIView):
    """GET /api/admin-dashboard/users/ — paginated user list with stats."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        role   = request.query_params.get('role', '')

        qs = User.objects.annotate(
            post_count_val = Count('posts',             distinct=True),
            flagged_count  = Count('moderation_requests',
                                   filter=Q(moderation_requests__status='FLAGGED'), distinct=True),
            blocked_count  = Count('moderation_requests',
                                   filter=Q(moderation_requests__status='BLOCKED'), distinct=True),
        ).order_by('-created_at')

        if search:
            qs = qs.filter(Q(username__icontains=search) | Q(email__icontains=search))
        if role == 'admin':
            qs = qs.filter(is_admin=True)
        elif role == 'moderator':
            qs = qs.filter(is_moderator=True)
        elif role == 'user':
            qs = qs.filter(is_admin=False, is_moderator=False)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [
            {
                'id':           u.id,
                'username':     u.username,
                'email':        u.email,
                'is_active':    u.is_active,
                'is_admin':     u.is_admin,
                'is_moderator': u.is_moderator,
                'post_count':   u.post_count_val,
                'flagged':      u.flagged_count,
                'blocked':      u.blocked_count,
                'joined':       u.created_at,
            }
            for u in page
        ]
        return paginator.get_paginated_response(data)


class AdminUserDetailView(APIView):
    """PATCH /api/admin-dashboard/users/<id>/ — toggle is_active / is_moderator."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def patch(self, request, user_id):
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return error_response(message='User not found.', status_code=404)

        allowed = {'is_active', 'is_moderator'}
        for field in allowed:
            if field in request.data:
                setattr(user, field, bool(request.data[field]))
        user.save(update_fields=list(allowed & set(request.data.keys())))
        return success_response({'id': user.id, 'is_active': user.is_active, 'is_moderator': user.is_moderator})


class AdminReportsListView(APIView):
    """GET /api/admin-dashboard/reports/ — all reports with filtering."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        status_filter = request.query_params.get('status', '')
        ctype_filter  = request.query_params.get('content_type', '')

        qs = Report.objects.select_related('reported_by', 'reviewed_by').order_by('-created_at')
        if status_filter:
            qs = qs.filter(status=status_filter.upper())
        if ctype_filter:
            qs = qs.filter(content_type=ctype_filter.lower())

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [
            {
                'id':           r.id,
                'reported_by':  r.reported_by.username,
                'content_type': r.content_type,
                'object_id':    r.object_id,
                'reason':       r.reason,
                'status':       r.status,
                'reviewed_by':  r.reviewed_by.username if r.reviewed_by else None,
                'created_at':   r.created_at,
            }
            for r in page
        ]
        return paginator.get_paginated_response(data)

    def patch(self, request, report_id=None):
        if not report_id:
            return error_response(message='report_id required.')
        try:
            report = Report.objects.get(pk=report_id)
        except Report.DoesNotExist:
            return error_response(message='Report not found.', status_code=404)

        new_status = request.data.get('status', '').upper()
        valid = {'PENDING', 'REVIEWED', 'RESOLVED', 'DISMISSED'}
        if new_status not in valid:
            return error_response(message=f'Status must be one of {valid}.')

        report.status      = new_status
        report.reviewed_by = request.user
        report.save(update_fields=['status', 'reviewed_by'])
        return success_response({'id': report.id, 'status': report.status})


class AdminModerationLogsView(APIView):
    """GET /api/admin-dashboard/moderation-logs/ — filterable moderation log."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        since    = _parse_date_range(request)
        status_f = request.query_params.get('status', '')
        modal_f  = request.query_params.get('modality', '')
        user_f   = request.query_params.get('username', '')

        qs = ModerationLog.objects.select_related('requested_by').filter(created_at__gte=since)
        if status_f:
            qs = qs.filter(status=status_f.upper())
        if modal_f:
            qs = qs.filter(modality=modal_f.lower())
        if user_f:
            qs = qs.filter(requested_by__username__icontains=user_f)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        data = [
            {
                'id':           log.id,
                'username':     log.requested_by.username if log.requested_by else 'Anonymous',
                'modality':     log.modality,
                'status':       log.status,
                'reason':       log.reason[:200] if log.reason else '',
                'confidence':   round(float(log.confidence), 1),
                'severity':     log.severity,
                'risk_level':   log.risk_level,
                'escalated':    log.escalated,
                'content_type': log.content_type,
                'object_id':    log.object_id,
                'created_at':   log.created_at,
            }
            for log in page
        ]
        return paginator.get_paginated_response(data)
