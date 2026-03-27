from django.urls import path
from .views import (
    AdminDashboardMetricsView,
    AdminUsersListView,
    AdminUserDetailView,
    AdminReportsListView,
    AdminModerationLogsView,
)

urlpatterns = [
    path('metrics/',                    AdminDashboardMetricsView.as_view(), name='admin-metrics'),
    path('users/',                      AdminUsersListView.as_view(),        name='admin-users'),
    path('users/<int:user_id>/',        AdminUserDetailView.as_view(),       name='admin-user-detail'),
    path('reports/',                    AdminReportsListView.as_view(),      name='admin-reports'),
    path('reports/<int:report_id>/',    AdminReportsListView.as_view(),      name='admin-report-update'),
    path('moderation-logs/',            AdminModerationLogsView.as_view(),   name='admin-mod-logs'),
]
