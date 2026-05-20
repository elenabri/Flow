from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail  
from .models import User, BloggerProfile, AdvertiserProfile  
from .constants import TOPIC_CHOICES
import secrets

class RegistrationForm(forms.ModelForm):
    # Явно объявляем email
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'})
    )
    
    # ВОЗВРАЩЕНО: Поле Телеграма
    telegram = forms.CharField(
        required=True,  # Сделайте False, если поле необязательное
        label="Telegram",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '@username или ссылка'})
    )
    
    username = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    role = forms.ChoiceField(
        choices=[('blogger', 'Блогер'), ('advertiser', 'Рекламодатель')], 
        label="Кто вы?",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # Поля Блогера
    channel_link = forms.CharField(
        required=False, 
        label="Ссылка на канал",
        widget=forms.TextInput(attrs={
            'placeholder': 'https://www.youtube.com/@yourchannel',
            'class': 'form-control'
        })
    )
    
    price_start = forms.DecimalField(required=False, label="Начало", initial=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    price_middle = forms.DecimalField(required=False, label="Середина", initial=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    price_end = forms.DecimalField(required=False, label="Конец", initial=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    price_shorts = forms.DecimalField(required=False, label="Shorts", initial=0, widget=forms.NumberInput(attrs={'class': 'form-control'}))
    
    topics = forms.MultipleChoiceField(
        choices=TOPIC_CHOICES, 
        widget=forms.CheckboxSelectMultiple, 
        required=False,
        label="Тематики"
    )

    # Поля Рекламодателя
    company_name = forms.CharField(required=False, label="Название компании", widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_title = forms.CharField(required=False, label="Название товара", widget=forms.TextInput(attrs={'class': 'form-control'}))
    product_link = forms.URLField(required=False, label="Ссылка на продукт", widget=forms.URLInput(attrs={'class': 'form-control'}))

    class Meta:
        model = User
        fields = ['username', 'email']

    # Валидация уникальности email
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email=email).exists():
                raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email

    # Логика сохранения, генерации пароля и создания профилей
    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data.get('email').lower()
        
        user.username = email
        
        # Автоматически генерируем случайный пароль
        #random_password = User.objects.make_random_password()
        random_password = secrets.token_urlsafe(16)
        user.password = make_password(random_password)
        
        if commit:
            user.save()  # Сохраняем пользователя
            
            # Отправляем сгенерированный пароль на email
            send_mail(
                subject='Доступ к платформе',
                message=f'Вы успешно зарегистрированы!\nВаш логин: {email}\nВаш временный пароль: {random_password}\n\nВы можете изменить его в личном кабинете.',
                from_email='noreply@yourdomain.com',  
                recipient_list=[email],
                fail_silently=False,
            )
            
            role = self.cleaned_data.get('role')
            telegram_data = self.cleaned_data.get('telegram')
            
            if role == 'blogger':
                BloggerProfile.objects.create(
                    user=user,  
                    telegram=telegram_data,  # Сохраняем телеграм в профиль блогера
                    channel_link=self.cleaned_data.get('channel_link'),
                    price_start=self.cleaned_data.get('price_start'),
                    price_middle=self.cleaned_data.get('price_middle'),
                    price_end=self.cleaned_data.get('price_end'),
                    price_shorts=self.cleaned_data.get('price_shorts'),
                )
                
            elif role == 'advertiser':
                AdvertiserProfile.objects.create(
                    user=user,  
                    telegram=telegram_data,  # Сохраняем телеграм в профиль рекламодателя
                    company_name=self.cleaned_data.get('company_name'),
                    product_title=self.cleaned_data.get('product_title'),
                    product_link=self.cleaned_data.get('product_link'),
                )
                
        return user


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
