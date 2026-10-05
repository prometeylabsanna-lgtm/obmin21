from django.contrib import admin, messages
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group, User
from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.http import HttpRequest
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

if admin.site.is_registered(User):
    admin.site.unregister(User)
if admin.site.is_registered(Group):
    admin.site.unregister(Group)


def _blocked_delete_reason(request: HttpRequest, user: User) -> str | None:
    if user.pk == request.user.pk:
        return 'Не можна видалити власний обліковий запис.'
    if user.is_superuser and not (
        User.objects.filter(is_superuser=True).exclude(pk=user.pk).exists()
    ):
        return 'Не можна видалити останнього адміністратора.'
    return None


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    def has_delete_permission(self, request, obj=None):
        if obj is not None and _blocked_delete_reason(request, obj):
            return False
        return super().has_delete_permission(request, obj)

    def delete_model(self, request, obj):
        reason = _blocked_delete_reason(request, obj)
        if reason:
            messages.error(request, reason)
            raise PermissionDenied(reason)
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset: QuerySet[User]):
        users = list(queryset)
        blocked, allowed = [], []
        for user in users:
            if user.pk == request.user.pk:
                blocked.append((user, 'не можна видалити власний обліковий запис'))
            else:
                allowed.append(user)
        allowed_ids = {u.pk for u in allowed}
        supers_remaining = set(
            User.objects.filter(is_superuser=True)
            .exclude(pk__in=allowed_ids)
            .values_list('pk', flat=True)
        )
        if not supers_remaining:
            kept = []
            for user in allowed:
                if user.is_superuser:
                    blocked.append((user, 'не можна видалити останнього адміністратора'))
                else:
                    kept.append(user)
            allowed = kept
        for user, reason in blocked:
            messages.warning(request, f'{user}: {reason}')
        if allowed:
            super().delete_queryset(request, User.objects.filter(pk__in=[u.pk for u in allowed]))


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass
