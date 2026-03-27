from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/',         include('apps.accounts.urls')),
    path('api/profiles/',     include('apps.profiles.urls')),
    path('api/posts/',        include('apps.posts.urls')),
    path('api/comments/',     include('apps.comments.urls')),
    path('api/interactions/', include('apps.interactions.urls')),
    path('api/moderation/',   include('apps.moderation.urls')),
    path('api/reports/',      include('apps.reports.urls')),
    path('api/analytics/',    include('apps.analytics_app.urls')),
    path('api/notifications/',include('apps.notifications.urls')),
    path('api/settings/',     include('apps.settingsapp.urls')),
    path('api/admin-dashboard/', include('apps.admin_dashboard.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
