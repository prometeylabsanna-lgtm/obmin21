from django import forms
from django.core.exceptions import ValidationError

from src.network.banner_concurrency import city_banner_stamp
from src.network.cms_proxies import BannerCity

STALE_BANNER_MESSAGE = (
    'Ці дані змінили в іншій вкладці або іншим користувачем. Оновіть сторінку.'
)


class BannerCityForm(forms.ModelForm):
    banner_stamp = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = BannerCity
        fields = (
            'banner_image',
            'banner_title',
            'banner_title_mode',
            'banner_suffix',
            'banner_suffix_mode',
            'banner_text',
            'banner_text_mode',
            'banner_button',
            'banner_button_mode',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['banner_stamp'].initial = city_banner_stamp(self.instance)

    def clean(self):
        cleaned = super().clean()
        stamp = (cleaned.get('banner_stamp') or '').strip()
        if self.instance.pk and stamp:
            current = city_banner_stamp(
                BannerCity.objects.get(pk=self.instance.pk),
            )
            if stamp != current:
                raise ValidationError(STALE_BANNER_MESSAGE)
        return cleaned
