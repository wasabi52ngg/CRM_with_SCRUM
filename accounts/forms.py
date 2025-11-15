from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django import forms
from .CustomWidgets import CustomClearableFileInput


class LoginUserForm(AuthenticationForm):
    """Форма входа с поддержкой email/username"""
    username = forms.CharField(label='Логин или Email', max_length=254)

    class Meta:
        model = get_user_model()
        fields = ['username', 'password']


class RegisterUserForm(UserCreationForm):
    """Форма регистрации пользователя"""
    username = forms.CharField(label='Логин')
    email = forms.EmailField(label='E-mail')
    first_name = forms.CharField(label='Имя')
    last_name = forms.CharField(label='Фамилия')
    phone = forms.CharField(label='Телефон')
    photo = forms.ImageField(label='Фото', required=False)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput())

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'photo', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('Такая почта уже существует')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        # Устанавливаем роль по умолчанию
        user.role = get_user_model().Role.CLIENT
        user.developer_type = get_user_model().DeveloperType.NONE
        if commit:
            user.save()
        return user


class ProfileUserForm(forms.ModelForm):
    """Форма редактирования профиля"""
    username = forms.CharField(disabled=True, label='Логин', widget=forms.TextInput(attrs={'class': 'form-input'}))
    email = forms.CharField(disabled=True, label='E-mail', widget=forms.TextInput(attrs={'class': 'form-input'}))
    photo = forms.ImageField(label='Выбрать новое фото', required=False, widget=CustomClearableFileInput)

    class Meta:
        model = get_user_model()
        fields = ['photo', 'username', 'email', 'first_name', 'last_name', 'phone']
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Телефон',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
        }


class UserPasswordChangeForm(PasswordChangeForm):
    """Форма смены пароля"""
    old_password = forms.CharField(label='Старый пароль', widget=forms.PasswordInput())
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput())
    new_password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput())

