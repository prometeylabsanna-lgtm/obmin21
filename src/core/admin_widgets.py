from __future__ import annotations

from typing import Any, Optional

from django.contrib.admin.widgets import AdminTextInputWidget, AdminTextareaWidget
from django.forms.widgets import ClearableFileInput, TextInput
from tinymce.widgets import TinyMCE
from unfold.widgets import INPUT_CLASSES, TEXTAREA_CLASSES


def _classes(base: list[str], extra: str = '') -> str:
    classes = list(base)
    if extra:
        for token in extra.split():
            if token and token not in classes:
                classes.append(token)
    return ' '.join(classes)


class CmsAdminTextInputWidget(AdminTextInputWidget):
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        super().__init__(attrs={
            **merged,
            'class': _classes(INPUT_CLASSES, extra),
        })


class CmsAdminTextareaWidget(AdminTextareaWidget):
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        super().__init__(attrs={
            **merged,
            'class': _classes(TEXTAREA_CLASSES, extra),
        })


class CmsAdminColorWidget(TextInput):
    template_name = 'django/forms/widgets/cms_color.html'
    input_type = 'color'

    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        merged['type'] = 'color'
        super().__init__(attrs={
            **merged,
            'class': _classes(['cms-color__swatch'], extra),
        })

    def format_value(self, value):
        raw = super().format_value(value) or ''
        if isinstance(raw, str) and len(raw) == 7 and raw.startswith('#'):
            return raw
        return '#ffffff'


class CmsAdminImageWidget(ClearableFileInput):
    template_name = 'django/forms/widgets/cms_image.html'

    def __init__(
        self,
        attrs: Optional[dict[str, Any]] = None,
        fallback_url: str = '',
        fit: str = 'cover',
    ) -> None:
        self.fallback_url = fallback_url
        self.fit = fit
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        merged.setdefault('accept', 'image/*')
        super().__init__(attrs={
            **merged,
            'class': _classes(
                [c for c in INPUT_CLASSES if c != 'max-w-2xl'] + ['cms-image-input'],
                extra,
            ),
        })

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        uploaded = ''
        if value:
            try:
                uploaded = getattr(value, 'url', '') or ''
            except ValueError:
                uploaded = ''
        preview_url = uploaded or self.fallback_url
        widget = context['widget']
        widget['preview_url'] = preview_url
        widget['is_fallback'] = bool(preview_url and not uploaded)
        widget['fit'] = self.fit
        return context


class CmsTinyMCE(TinyMCE):
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        super().__init__(
            attrs=attrs,
            mce_attrs={
                'height': 360,
                'menubar': False,
                'plugins': 'link lists',
                'toolbar': 'undo redo | bold italic underline | bullist numlist | link',
                'promotion': False,
                'branding': False,
                'forced_root_block': 'p',
                'newline_behavior': 'block',
            },
        )
