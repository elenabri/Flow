from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import make_password
from .models import User, ProductAd, KktuCode  # Предполагаем, что профили лежат тут же
from .constants import TOPIC_CHOICES

class RegistrationForm(forms.ModelForm):
    # Явно объявляем email с правильным виджетом
    email = forms.EmailField(
        label="Электронная почта",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.com'})
    )
    
    # Поля для паролей
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'})
    )
    password_confirm = forms.CharField(
        label="Подтвердите пароль",
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '********'})
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

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с такой почтой уже зарегистрирован.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "Пароли не совпадают.")
        
        return cleaned_data

    def save(self, commit=True):
        """
        Переопределяем сохранение, чтобы автоматически генерировать username 
        из email, хэшировать пароль и сохранять дополнительные поля.
        """
        user = super().save(commit=False)
        email = self.cleaned_data.get('email')
        
        # Автоматически ставим username равным email (для совместимости с Django)
        user.username = email
        user.password = make_password(self.cleaned_data.get('password'))
        
        if commit:
            user.save()
            
            # Логика создания связанных профилей (адаптируйте под ваши модели профилей)
            role = self.cleaned_data.get('role')
            if role == 'blogger':
                # Пример создания профиля блогера:
                # BloggerProfile.objects.create(
                #     user=user,
                #     channel_link=self.cleaned_data.get('channel_link'),
                #     price_start=self.cleaned_data.get('price_start'),
                #     ...
                # )
                pass
            elif role == 'advertiser':
                # Пример создания профиля рекламодателя:
                # AdvertiserProfile.objects.create(
                #     user=user,
                #     company_name=self.cleaned_data.get('company_name'),
                #     ...
                # )
                pass
                
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


class ProductAdForm(forms.ModelForm):
    kktu_choice = forms.ModelChoiceField(
        queryset=KktuCode.objects.all(),
        label="Категория товара для ОРД",
        widget=forms.Select(attrs={'class': 'form-control select2'}),
        empty_label="Выберите категорию ККТУ"
    )

    class Meta:
        model = ProductAd
        # ИСПРАВЛЕНО: убрано многоточие, заменено на стандартные явные поля модели
        fields = ['name', 'description', 'kktu_choice'] 
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Судак свежемороженый'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
