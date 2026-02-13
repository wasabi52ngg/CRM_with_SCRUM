from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django import forms
from .CustomWidgets import CustomClearableFileInput
from crm.models import Company, CompanyMembership


class LoginUserForm(AuthenticationForm):
    """Форма входа с поддержкой email/username"""
    username = forms.CharField(label='Логин или Email', max_length=254)

    class Meta:
        model = get_user_model()
        fields = ['username', 'password']


class RegisterUserForm(UserCreationForm):
    """Форма регистрации пользователя (клиент / обычный пользователь)"""
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
        # Устанавливаем роль по умолчанию для обычного зарегистрированного пользователя
        user.role = get_user_model().Role.CLIENT
        user.developer_type = get_user_model().DeveloperType.NONE
        if commit:
            user.save()
        return user


class CompanyRegisterForm(UserCreationForm):
    """
    Регистрация компании и первого пользователя‑владельца.
    Это основной вход в систему для IT‑компаний (аналог создания организации в Jira).
    """

    # Поля пользователя
    username = forms.CharField(label='Логин')
    email = forms.EmailField(label='E-mail')
    first_name = forms.CharField(label='Имя')
    last_name = forms.CharField(label='Фамилия')
    phone = forms.CharField(label='Телефон')
    photo = forms.ImageField(label='Фото', required=False)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput())

    # Поля компании
    company_name = forms.CharField(label='Название компании')
    company_slug = forms.SlugField(
        label='Короткий идентификатор (slug)',
        help_text='Используется в ссылке для клиентов, только латиница, цифры и дефис',
    )
    company_description = forms.CharField(
        label='Описание компании',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )
    company_industry = forms.CharField(
        label='Сфера деятельности компании',
        required=False,
    )

    class Meta:
        model = get_user_model()
        fields = [
            'company_name',
            'company_slug',
            'company_description',
            'company_industry',
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'photo',
            'password1',
            'password2',
        ]

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('Такая почта уже существует')
        return email

    def clean_company_slug(self):
        slug = self.cleaned_data['company_slug']
        if Company.objects.filter(slug=slug).exists():
            raise forms.ValidationError('Компания с таким идентификатором уже существует')
        return slug

    def save(self, commit=True):
        """
        Создаёт:
        - компанию;
        - пользователя с ролью MANAGER;
        - запись CompanyMembership с ролью OWNER.
        """
        UserModel = get_user_model()
        user = super().save(commit=False)
        user.role = UserModel.Role.MANAGER
        user.developer_type = UserModel.DeveloperType.NONE

        company = Company(
            name=self.cleaned_data['company_name'],
            slug=self.cleaned_data['company_slug'],
            description=self.cleaned_data.get('company_description', ''),
            industry=self.cleaned_data.get('company_industry', ''),
        )

        if commit:
            company.save()
            user.save()
            CompanyMembership.objects.create(
                company=company,
                user=user,
                role=CompanyMembership.Role.OWNER,
            )
        else:
            # В дипломном проекте commit=False практически не используется,
            # но для корректности оставляем вариант без сохранения.
            self._company_instance = company

        return user


class CompanyUserRegisterForm(UserCreationForm):
    """
    Регистрация сотрудника в уже существующей компании по секретному коду.
    """

    username = forms.CharField(label='Логин')
    email = forms.EmailField(label='E-mail')
    first_name = forms.CharField(label='Имя')
    last_name = forms.CharField(label='Фамилия')
    phone = forms.CharField(label='Телефон')
    photo = forms.ImageField(label='Фото', required=False)
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput())

    company_code = forms.CharField(
        label='Код компании',
        help_text='Секретный код, который вы получили от администратора компании',
    )

    class Meta:
        model = get_user_model()
        fields = [
            'username',
            'email',
            'first_name',
            'last_name',
            'phone',
            'photo',
            'password1',
            'password2',
            'company_code',
        ]

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('Такая почта уже существует')
        return email

    def clean_company_code(self):
        code = self.cleaned_data['company_code']
        if not Company.objects.filter(join_code=code).exists():
            raise forms.ValidationError('Компания с таким кодом не найдена')
        return code

    def save(self, commit=True):
        """
        Создаёт пользователя и привязывает его к компании по коду как разработчика.
        """
        UserModel = get_user_model()
        user = super().save(commit=False)
        user.role = UserModel.Role.DEVELOPER
        # developer_type можно оставить NONE по умолчанию, пусть выбирает в профиле

        company = Company.objects.get(join_code=self.cleaned_data['company_code'])

        if commit:
            user.save()
            CompanyMembership.objects.create(
                company=company,
                user=user,
                role=CompanyMembership.Role.DEVELOPER,
            )

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

