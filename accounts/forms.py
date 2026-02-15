from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, PasswordChangeForm
from django import forms
from django.utils.text import slugify
from .CustomWidgets import CustomClearableFileInput
from crm.models import Company, CompanyMembership


def transliterate_to_latin(text):
    """Транслитерация кириллицы в латиницу для slug"""
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    }
    result = ''
    for char in text:
        result += translit_map.get(char, char)
    return result


class LoginUserForm(AuthenticationForm):
    """Форма входа с поддержкой email/username"""
    username = forms.CharField(label='Логин или Email', max_length=254)

    class Meta:
        model = get_user_model()
        fields = ['username', 'password']


class RegisterUserForm(UserCreationForm):
    """
    Форма регистрации пользователя.
    Пользователь выбирает: сотрудник или клиент.
    Если сотрудник - нужен код компании, создаётся запрос на участие.
    """
    USER_TYPE_CHOICES = [
        ('employee', 'Сотрудник'),
        ('client', 'Клиент'),
    ]
    
    username = forms.CharField(label='Логин')
    email = forms.EmailField(label='E-mail')
    first_name = forms.CharField(label='Имя')
    last_name = forms.CharField(label='Фамилия')
    phone = forms.CharField(label='Телефон')
    photo = forms.ImageField(label='Фото', required=False)
    user_type = forms.ChoiceField(
        label='Тип пользователя',
        choices=USER_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='client',
        help_text='Выберите, регистрируетесь ли вы как сотрудник компании или как клиент',
    )
    company_code = forms.CharField(
        label='Код компании',
        max_length=16,
        help_text='Введите секретный код компании, который вам предоставил администратор',
        required=False,
    )
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput())
    password2 = forms.CharField(label='Повторите пароль', widget=forms.PasswordInput())

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'first_name', 'last_name', 'phone', 'photo', 'user_type', 'company_code', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email=email).exists():
            raise forms.ValidationError('Такая почта уже существует')
        return email

    def clean(self):
        cleaned_data = super().clean()
        user_type = cleaned_data.get('user_type')
        company_code = cleaned_data.get('company_code', '').strip()
        
        # Если выбран сотрудник, код компании обязателен
        if user_type == 'employee' and not company_code:
            raise forms.ValidationError({
                'company_code': 'Для регистрации сотрудника необходимо указать код компании'
            })
        
        # Если указан код компании, проверяем его существование
        if company_code:
            if not Company.objects.filter(join_code=company_code).exists():
                raise forms.ValidationError({
                    'company_code': 'Компания с таким кодом не найдена'
                })
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user_type = self.cleaned_data.get('user_type')
        company_code = self.cleaned_data.get('company_code', '').strip()
        
        # Устанавливаем роль в зависимости от типа пользователя
        if user_type == 'employee':
            user.role = get_user_model().Role.DEVELOPER
        else:
            user.role = get_user_model().Role.CLIENT
        
        user.developer_type = get_user_model().DeveloperType.NONE
        
        if commit:
            user.save()
            # Если сотрудник с кодом компании, создаём запрос на участие
            if user_type == 'employee' and company_code:
                company = Company.objects.get(join_code=company_code)
                CompanyMembership.objects.create(
                    company=company,
                    user=user,
                    is_manager=False,  # Админ выберет роли при подтверждении
                    is_developer=False,
                    is_approved=False,  # Требует подтверждения администратора
                )
        
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
    company_description = forms.CharField(
        label='Описание компании',
        widget=forms.Textarea(attrs={'rows': 3}),
        required=False,
    )
    company_industry = forms.CharField(
        label='Сфера деятельности компании (необязательно)',
        required=False,
    )

    class Meta:
        model = get_user_model()
        fields = [
            'company_name',
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

    def clean_company_name(self):
        company_name = self.cleaned_data['company_name']
        # Сначала транслитерируем кириллицу в латиницу, затем создаем slug
        transliterated = transliterate_to_latin(company_name)
        base_slug = slugify(transliterated)
        
        # Если после транслитерации и slugify получилась пустая строка, используем fallback
        if not base_slug:
            # Пробуем создать slug из первых букв/цифр
            base_slug = slugify(company_name.replace(' ', '-').lower()[:20])
            if not base_slug:
                # Если все еще пусто, используем просто "company" + случайное число
                import random
                base_slug = f"company-{random.randint(1000, 9999)}"
        
        # Проверяем уникальность slug
        slug = base_slug
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        
        # Сохраняем сгенерированный slug для использования в save()
        self._generated_slug = slug
        return company_name

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
            slug=getattr(self, '_generated_slug', slugify(self.cleaned_data['company_name'])),
            description=self.cleaned_data.get('company_description', ''),
            industry=self.cleaned_data.get('company_industry', ''),
        )

        if commit:
            company.save()
            user.save()
            CompanyMembership.objects.create(
                company=company,
                user=user,
                is_owner=True,  # Владелец компании
                is_manager=True,  # Владелец имеет все права
                is_developer=True,
                is_approved=True,  # Владелец автоматически подтверждён
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
        fields = ['photo', 'username', 'email', 'first_name', 'last_name', 'phone', 'developer_type']
        labels = {
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'phone': 'Телефон',
            'developer_type': 'Тип разработчика',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'developer_type': forms.Select(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        UserModel = get_user_model()
        # Тип разработчика показываем только разработчикам (по роли или по участию в компании)
        if self.instance:
            is_dev = (
                self.instance.role == UserModel.Role.DEVELOPER
                or self.instance.company_memberships.filter(
                    is_approved=True, is_developer=True
                ).exists()
            )
            if not is_dev:
                self.fields.pop('developer_type', None)


class UserPasswordChangeForm(PasswordChangeForm):
    """Форма смены пароля"""
    old_password = forms.CharField(label='Старый пароль', widget=forms.PasswordInput())
    new_password1 = forms.CharField(label='Новый пароль', widget=forms.PasswordInput())
    new_password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput())

