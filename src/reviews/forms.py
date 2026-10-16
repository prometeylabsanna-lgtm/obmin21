from django import forms

from src.network.models import City
from src.reviews.models import Review


class ReviewForm(forms.ModelForm):
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

    def clean_rating(self):
        rating = self.cleaned_data.get('rating') or 5
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 5
        return max(1, min(5, rating))

    def clean_consent(self):
        consent = self.cleaned_data.get('consent')
        if not consent:
            raise forms.ValidationError('Потрібна згода на обробку даних')
        return consent
