from dataclasses import replace

from django.contrib import admin, messages
from django.http import HttpResponseForbidden, HttpResponseNotAllowed, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import reverse
from unfold.admin import ModelAdmin
from unfold.decorators import action

from src.core import admin_auth  # noqa: F401
from src.core.admin_mixins import SingletonUnfoldAdmin
from src.core.exchange_mode import is_mode_forced_by_env
from src.core.exchange_preview import (
    ENV_LOCK_NOTICE,
    ExchangeOnlyToggleRejected,
    build_hide_report,
    confirm_label,
    mode_button_label,
    stored_exchange_only,
    toggle_exchange_only,
)
from src.core.models import ExchangeModeLog, FooterSettings, HeaderSettings, SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(SingletonUnfoldAdmin):
    actions_detail = ('exchange_only_preview',)
    change_form_outer_before_template = 'admin/core/exchange_only_notice.html'
    content_fields = (
        'site_name',
        'rate_hold_minutes',
        'hidden_page_status',
        'retry_after_seconds',
        'telegram_url',
        'youtube_url',
        'instagram_url',
        'facebook_url',
        'notify_email',
        'notify_telegram_chat_id',
    )
    style_fields = ()

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra = dict(extra_context or {})
        enabled = stored_exchange_only()
        extra.update({
            'exchange_mode_forced': is_mode_forced_by_env(),
            'exchange_mode_enabled': enabled,
            'exchange_mode_label': mode_button_label(enabled),
            'exchange_mode_lock_notice': ENV_LOCK_NOTICE,
        })
        return super().changeform_view(request, object_id, form_url, extra)

    def get_actions_detail(self, request, object_id):
        actions = super().get_actions_detail(request, object_id)
        if is_mode_forced_by_env():
            return [
                item for item in actions
                if not item.action_name.endswith('_exchange_only_preview')
            ]
        label = mode_button_label(stored_exchange_only())
        renamed = []
        for item in actions:
            if item.action_name.endswith('_exchange_only_preview'):
                renamed.append(replace(item, description=label))
            else:
                renamed.append(item)
        return renamed

    @action(
        description='Увімкнути режим «Лише обмін валют»',
        url_path='exchange-only',
        icon='toggle_on',
        permissions=['change'],
    )
    def exchange_only_preview(self, request, object_id):
        if request.method == 'POST':
            try:
                row = toggle_exchange_only(request.user)
            except ExchangeOnlyToggleRejected as exc:
                return HttpResponseForbidden(str(exc))
            if row.exchange_only:
                messages.success(request, 'Режим «Лише обмін валют» увімкнено.')
            else:
                messages.success(request, 'Режим «Лише обмін валют» вимкнено.')
            return HttpResponseRedirect(
                reverse('admin:core_sitesettings_change', args=[row.pk]),
            )
        if request.method != 'GET':
            return HttpResponseNotAllowed(['GET', 'POST'])
        enabled = stored_exchange_only()
        context = {
            **self.admin_site.each_context(request),
            'title': 'Що буде сховано',
            'opts': self.opts,
            'report': build_hide_report(),
            'exchange_mode_forced': is_mode_forced_by_env(),
            'exchange_mode_enabled': enabled,
            'exchange_mode_label': mode_button_label(enabled),
            'exchange_mode_lock_notice': ENV_LOCK_NOTICE,
            'confirm_label': confirm_label(enabled),
        }
        return TemplateResponse(
            request,
            'admin/core/exchange_hide_preview.html',
            context,
        )


@admin.register(HeaderSettings)
class HeaderSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'header_logo',
    )
    style_fields = (
        'header_color_bg',
        'header_color_text',
        'header_color_accent',
        'header_color_highlight',
    )


@admin.register(FooterSettings)
class FooterSettingsAdmin(SingletonUnfoldAdmin):
    content_fields = (
        'footer_logo',
        'footer_copy',
    )
    style_fields = (
        'footer_color_bg',
        'footer_color_text',
        'footer_color_accent',
        'footer_color_highlight',
    )


@admin.register(ExchangeModeLog)
class ExchangeModeLogAdmin(ModelAdmin):
    list_display = ('created_at', 'user', 'from_value', 'to_value', 'source')
    list_filter = ('source', 'from_value', 'to_value')
    ordering = ('-created_at',)
    readonly_fields = ('user', 'created_at', 'from_value', 'to_value', 'source')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
