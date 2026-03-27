from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering        = ('email',)
    list_display    = ('email', 'username', 'is_staff', 'is_moderator', 'is_active')
    fieldsets       = (
        (None,           {'fields': ('email', 'username', 'password')}),
        ('Permissions',  {'fields': ('is_active', 'is_staff', 'is_moderator', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets   = (
        (None, {'fields': ('email', 'username', 'password1', 'password2')}),
    )
    search_fields   = ('email', 'username')
    filter_horizontal = ('groups', 'user_permissions')
