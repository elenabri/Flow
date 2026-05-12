from django import forms
from .models import User
from django.contrib.auth.forms import AuthenticationForm
from .constants import TOPIC_CHOICES

class RegistrationForm(forms.ModelForm):
    # ИСПРАВЛЕНО: CharField вместо URLField, так как сюда пишем email
    username = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    role = forms.ChoiceField(
        choices=[('blogger', 'Блогер'), ('advertiser', 'Рекламодатель')], 
        label="Кто вы?"
    )
    
    # Ссылка на канал как CharField — это ок, если в модели BloggerProfile 
    # мы будем сохранять её аккуратно (проверяя наличие http)
    channel_link = forms.CharField(
        required=False, 
        label="Ссылка на канал",
        widget=forms.TextInput(attrs={
            'placeholder': 'https://www.youtube.com/@yourchannel',
            'class': 'form-control'
        })
    )
    
    # Добавлен initial=0 для стабильности DecimalField
    price_start = forms.DecimalField(required=False, label="Начало", initial=0)
    price_middle = forms.DecimalField(required=False, label="Середина", initial=0)
    price_end = forms.DecimalField(required=False, label="Конец", initial=0)
    price_shorts = forms.DecimalField(required=False, label="Shorts", initial=0)
    
    topics = forms.MultipleChoiceField(
        choices=TOPIC_CHOICES, 
        widget=forms.CheckboxSelectMultiple, 
        required=False,
        label="Тематики"
    )

    company_name = forms.CharField(required=False, label="Название компании")
    product_title = forms.CharField(required=False, label="Название товара")
    product_link = forms.URLField(required=False, label="Ссылка на продукт")

    # Валидация уникальности email
    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email

    class Meta:
        model = User
        fields = ['username', 'email']

class EmailLoginForm(AuthenticationForm):
    username = forms.EmailField(
        label="Почта", 
        widget=forms.EmailInput(attrs={
            'placeholder': 'example@mail.com',
            'class': 'form-control'
        })
    )
    password = forms.CharField(
        label="Пароль", 
        widget=forms.PasswordInput(attrs={
            'placeholder': '********',
            'class': 'form-control'
        })
    )
