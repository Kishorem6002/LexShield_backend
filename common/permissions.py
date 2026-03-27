from rest_framework.permissions import BasePermission


class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        from rest_framework.permissions import SAFE_METHODS
        if request.method in SAFE_METHODS:
            return True
        return obj.user == request.user


class IsModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and getattr(request.user, 'is_moderator', False)


class IsAdmin(BasePermission):
    """Only users with is_admin=True can access."""
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            getattr(request.user, 'is_admin', False) or request.user.is_superuser
        )


class IsAdminOrModerator(BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or
            getattr(request.user, 'is_moderator', False) or
            getattr(request.user, 'is_admin', False)
        )
