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
        # 1. Сначала сохраняем самого пользователя (базовые поля: email, username, password)
        user = super().save(commit=False)
        email = self.cleaned_data.get('email')
        
        user.username = email
        user.password = make_password(self.cleaned_data.get('password'))
        
        if commit:
            user.save()  # Сохраняем User в базу данных, чтобы получить его id
            
            # 2. Вытаскиваем роль, выбранную на форме
            role = self.cleaned_data.get('role')
            
            if role == 'blogger':
                # Создаем реальную запись в таблице блогеров
                # ВНИМАНИЕ: Замените BloggerProfile на ваше название модели (например, Blogger)
                BloggerProfile.objects.create(
                    user=user,  # Связываем профиль с созданным пользователем
                    channel_link=self.cleaned_data.get('channel_link'),
                    price_start=self.cleaned_data.get('price_start'),
                    price_middle=self.cleaned_data.get('price_middle'),
                    price_end=self.cleaned_data.get('price_end'),
                    price_shorts=self.cleaned_data.get('price_shorts'),
                    # Для ManyToMany (темы) нужен другой подход, он описан ниже
                )
                
                # Если у вас темы сохраняются в профиль блогера как ManyToMany:
                # blogger_profile.topics.set(self.cleaned_data.get('topics'))
                
            elif role == 'advertiser':
                # Создаем реальную запись в таблице рекламодателей
                # ВНИМАНИЕ: Замените AdvertiserProfile на ваше название модели
                AdvertiserProfile.objects.create(
                    user=user,  # Связываем профиль с созданным пользователем
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
