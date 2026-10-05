from django import forms

from src.reviews.models import Review


class ReviewForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['rating'].initial = 5
        self.fields['rating'].required = False

    class Meta:
        model = Review
        fields = ['name', 'text', 'city_name', 'consent', 'rating']
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
