from django import forms

from src.core.phones import normalize_ua_phone
from src.core.plain_text import plain_text
from src.network.models import City
from src.reviews.models import Review


class ReviewForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        label='',
        widget=forms.TextInput(attrs={
            'class': 'form__hp',
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].initial = 5
        self.fields['rating'].required = False
        self.fields['phone'].required = False
        names = list(
            City.objects.filter(is_active=True).order_by('sort_order', 'name').values_list('name', flat=True)
        )
        if names:
            self.fields['city_name'].widget = forms.Select(
                attrs={'class': 'form__input'},
                choices=[('', 'Місто')] + [(name, name) for name in names],
            )

    class Meta:
        model = Review
        fields = ['name', 'text', 'city_name', 'phone', 'consent', 'rating']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form__input',
                'autocomplete': 'name',
                'placeholder': "Ваше ім'я",
            }),
            'text': forms.Textarea(attrs={
                'class': 'form__input form__textarea',
                'rows': 4,
                'placeholder': 'Розкажіть, як пройшов обмін',
                'maxlength': '300',
            }),
            'city_name': forms.TextInput(attrs={
                'class': 'form__input',
                'placeholder': 'Місто',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form__input',
                'type': 'tel',
                'inputmode': 'tel',
                'autocomplete': 'tel',
                'placeholder': 'Телефон (необов’язково)',
            }),
            'consent': forms.CheckboxInput(attrs={'class': 'form__checkbox'}),
            'rating': forms.HiddenInput(),
        }

    def clean_website(self):
        if (self.cleaned_data.get('website') or '').strip():
            raise forms.ValidationError('Спам-запит відхилено')
        return ''

    def clean_text(self):
        return plain_text(self.cleaned_data.get('text') or '')

    def clean_phone(self):
        raw = self.cleaned_data.get('phone') or ''
        if not raw.strip():
            return ''
        normalized = normalize_ua_phone(raw)
        if not normalized:
            raise forms.ValidationError(
                'Вкажіть телефон у форматі +380XXXXXXXXX',
            )
        return normalized

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating in (None, ''):
            return 5
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            raise forms.ValidationError('Оцінка має бути від 1 до 5') from None
        if rating < 1 or rating > 5:
            raise forms.ValidationError('Оцінка має бути від 1 до 5')
        return rating

    def clean_consent(self):
        consent = self.cleaned_data.get('consent')
        if not consent:
            raise forms.ValidationError('Потрібна згода на обробку даних')
        return consent
