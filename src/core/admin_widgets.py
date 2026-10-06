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
        flag_code: str = '',
        flag_mark: str = '',
    ) -> None:
        self.fallback_url = fallback_url
        self.fit = fit
        self.flag_code = flag_code
        self.flag_mark = flag_mark
        merged = dict(attrs or {})
        extra = merged.pop('class', '')
        merged.setdefault('accept', 'image/jpeg,image/png,image/webp,image/gif')
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
        widget['flag_code'] = self.flag_code
        widget['flag_mark'] = self.flag_mark
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
                'language': 'uk',
                'forced_root_block': 'p',
                'newline_behavior': 'block',
                'extended_valid_elements': 'span[class],strong/b,em/i,a[href|target],ul,ol,li,p,br',
                'verify_html': False,
                'content_style': (
                    'body{font-size:14px;line-height:1.45;}'
                    'li{margin:0.4em 0;}'
                    'li span::after,li strong::before{content:" — ";}'
                    'li span + strong::before{content:none;}'
                    'li strong{font-weight:700;}'
                ),
            },
        )
