from django import forms

from src.leads.models import ContactMessage, ExchangeRequest
from src.leads.services import validate_phone
from src.network.models import Branch
from src.network.selectors import get_city_branches
from src.rates.models import CurrencyPair, RateBoard
from src.rates.selectors import get_quote


class ExchangeRequestForm(forms.ModelForm):
    class Meta:
        model = ExchangeRequest
        fields = [
            'name',
            'phone',
            'messenger',
            'pair',
            'board',
            'direction',
            'amount_give',
            'amount_receive',
            'rate_fixed',
            'branch',
            'consent',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form__input',
                'autocomplete': 'name',
                'required': True,
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form__input',
                'type': 'tel',
                'autocomplete': 'tel',
                'inputmode': 'tel',
                'required': True,
            }),
            'messenger': forms.TextInput(attrs={'class': 'form__input'}),
            'pair': forms.Select(attrs={'class': 'form__input'}),
            'board': forms.Select(attrs={'class': 'form__input'}),
            'direction': forms.Select(attrs={'class': 'form__input'}),
            'amount_give': forms.NumberInput(attrs={
                'class': 'form__input',
                'step': '0.01',
                'min': '0',
            }),
            'amount_receive': forms.NumberInput(attrs={
                'class': 'form__input',
                'step': '0.01',
                'min': '0',
            }),
            'rate_fixed': forms.HiddenInput(),
            'branch': forms.Select(attrs={'class': 'form__input'}),
            'consent': forms.CheckboxInput(attrs={'class': 'form__checkbox'}),
        }

    def __init__(self, *args, city=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.city = city
        self.fields['pair'].queryset = CurrencyPair.objects.filter(is_active=True)
        self.fields['board'].choices = RateBoard.choices
        self.fields['rate_fixed'].required = False
        if city is not None:
            self.fields['branch'].queryset = get_city_branches(city)
        else:
            self.fields['branch'].queryset = Branch.objects.none()

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not validate_phone(phone):
            raise forms.ValidationError('Вкажіть коректний телефон')
        return phone

    def clean_consent(self):
        consent = self.cleaned_data.get('consent')
        if not consent:
            raise forms.ValidationError('Потрібна згода на обробку даних')
        return consent

    def clean(self):
        cleaned = super().clean()
        pair = cleaned.get('pair')
        direction = cleaned.get('direction') or 'sell'
        board = cleaned.get('board') or RateBoard.RETAIL
        rate = cleaned.get('rate_fixed')
        if pair and rate is None:
            quote = get_quote(pair, self.city, board)
            if quote is None:
                self.add_error('pair', 'Немає курсу для цієї пари')
            else:
                cleaned['rate_fixed'] = quote.buy if direction == 'sell' else quote.sell
        return cleaned


class ContactMessageForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ['name', 'phone', 'message', 'consent']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form__input',
                'autocomplete': 'name',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form__input',
                'type': 'tel',
                'autocomplete': 'tel',
                'inputmode': 'tel',
            }),
            'message': forms.Textarea(attrs={
                'class': 'form__input form__textarea',
                'rows': 3,
            }),
            'consent': forms.CheckboxInput(attrs={'class': 'form__checkbox'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data['phone']
        if not validate_phone(phone):
            raise forms.ValidationError('Вкажіть коректний телефон')
        return phone

    def clean_consent(self):
        consent = self.cleaned_data.get('consent')
        if not consent:
            raise forms.ValidationError('Потрібна згода на обробку даних')
        return consent
