from django import forms

from src.rates.models import Quote


class QuoteAdminForm(forms.ModelForm):
    """Форма курсу: full_clean моделі (межі buy/sell) для адмінки й list_editable."""

    class Meta:
        model = Quote
        fields = '__all__'
