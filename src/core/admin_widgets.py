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
    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        merged['type'] = 'color'
        super().__init__(attrs={
            **merged,
            'class': _classes(INPUT_CLASSES, extra),
        })


class CmsAdminImageWidget(ClearableFileInput):
    template_name = 'django/forms/widgets/cms_image.html'

    def __init__(self, attrs: Optional[dict[str, Any]] = None) -> None:
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
        preview_url = ''
        if value:
            try:
                preview_url = getattr(value, 'url', '') or ''
            except ValueError:
                preview_url = ''
        context['widget']['preview_url'] = preview_url
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
