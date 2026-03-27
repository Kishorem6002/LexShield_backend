from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from common.mixins import TimestampMixin
from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin, TimestampMixin):
    email        = models.EmailField(unique=True)
    username     = models.CharField(max_length=50, unique=True)
    is_active    = models.BooleanField(default=True)
    is_staff     = models.BooleanField(default=False)
    is_moderator = models.BooleanField(default=False)
    is_admin     = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD  = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email
