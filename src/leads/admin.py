from django import forms
from django.contrib import admin, messages
from django.db.models import Q
from unfold.forms import ActionForm
from unfold.widgets import UnfoldAdminSelectWidget

from src.core.admin_mixins import ListUnfoldAdmin
from src.leads.models import ContactMessage, ExchangeRequest
from src.network.models import Branch


class ExchangeRequestActionForm(ActionForm):
    new_status = forms.ChoiceField(
        label='Новий статус',
        required=False,
        choices=[('', '— новий статус —'), *ExchangeRequest.Status.choices],
        widget=UnfoldAdminSelectWidget,
    )


def active_branch_queryset(current_branch_id=None):
    """Лише активні відділення в активних містах (+ поточне, щоб не зламати стару заявку)."""
    cond = Q(is_active=True, city__is_active=True)
    if current_branch_id:
        cond |= Q(pk=current_branch_id)
    return Branch.objects.filter(cond).select_related('city')


@admin.register(ExchangeRequest)
class ExchangeRequestAdmin(ListUnfoldAdmin):
    list_display = (
        'id',
        'name',
        'phone',
        'pair',
        'direction',
        'city',
        'status',
        'source',
        'created_at',
    )
    list_filter = ('status', 'city', ('created_at', admin.DateFieldListFilter), 'source', 'direction')
    search_fields = ('name', 'phone')
    readonly_fields = ('created_at', 'expires_at', 'rate_fixed')
    action_form = ExchangeRequestActionForm
    actions = ('change_status',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'branch':
            current = None
            obj_id = getattr(getattr(request, 'resolver_match', None), 'kwargs', {}).get('object_id')
            if obj_id:
                current = (
                    ExchangeRequest.objects.filter(pk=obj_id)
                    .values_list('branch_id', flat=True)
                    .first()
                )
            kwargs['queryset'] = active_branch_queryset(current)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    @admin.action(description='Змінити статус', permissions=['change'])
    def change_status(self, request, queryset):
        new_status = (request.POST.get('new_status') or '').strip()
        labels = dict(ExchangeRequest.Status.choices)
        if new_status not in labels:
            self.message_user(
                request,
                'Оберіть новий статус у списку поруч із дією.',
                level=messages.WARNING,
            )
            return
        changed = 0
        for obj in queryset:
            if obj.status == new_status:
                continue
            old_label = labels.get(obj.status, obj.status)
            obj.status = new_status
            obj.save(update_fields=['status'])
            self.log_change(
                request,
                obj,
                f'Статус: {old_label} → {labels[new_status]} (дія «Змінити статус»)',
            )
            changed += 1
        self.message_user(
            request,
            f'Статус «{labels[new_status]}» встановлено для заявок: {changed}.',
            level=messages.SUCCESS,
        )


@admin.register(ContactMessage)
class ContactMessageAdmin(ListUnfoldAdmin):
    list_display = ('id', 'name', 'phone', 'city', 'source', 'is_processed', 'created_at')
    list_filter = ('is_processed', 'city', 'source')
    search_fields = ('name', 'phone', 'message')
