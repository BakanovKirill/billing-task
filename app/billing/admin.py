from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as UserAdminBase

from billing.models import User


class UserAdmin(UserAdminBase):
    pass


admin.site.register(User, UserAdmin)
