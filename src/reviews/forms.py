from django import forms

from src.reviews.models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['name', 'text', 'city_name', 'consent']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form__input', 'autocomplete': 'name'}),
            'text': forms.Textarea(attrs={'class': 'form__input form__textarea', 'rows': 4}),
            'city_name': forms.TextInput(attrs={'class': 'form__input'}),
            'consent': forms.CheckboxInput(attrs={'class': 'form__checkbox'}),
        }

    def clean_consent(self):
        consent = self.cleaned_data.get('consent')
        if not consent:
            raise forms.ValidationError('Потрібна згода на обробку даних')
        return consent
