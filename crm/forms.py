from django import forms
from django.contrib.auth import get_user_model

from .models import CompanyMembership


class CompanyMemberAddForm(forms.Form):
    """
    Простая форма добавления участника компании по email и роли.
    Используется владельцем/менеджером компании в настройках.
    """

    email = forms.EmailField(label="E-mail пользователя")
    role = forms.ChoiceField(
        label="Роль в компании",
        choices=CompanyMembership.Role.choices,
        initial=CompanyMembership.Role.DEVELOPER,
    )

    def __init__(self, *args, **kwargs):
        self.company = kwargs.pop("company", None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data["email"]
        User = get_user_model()
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Пользователь с таким e-mail не найден. Сначала зарегистрируйтесь в системе.")
        return email

    def save(self):
        """
        Создаёт CompanyMembership, если его ещё нет.
        """
        from .models import CompanyMembership
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.get(email=self.cleaned_data["email"])
        membership, _ = CompanyMembership.objects.get_or_create(
            company=self.company,
            user=user,
            defaults={"role": self.cleaned_data["role"]},
        )
        if not _:
            # Если уже был участник — просто обновим роль
            membership.role = self.cleaned_data["role"]
            membership.save(update_fields=["role"])
        return membership

