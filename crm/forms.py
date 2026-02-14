from django import forms
from django.contrib.auth import get_user_model

from .models import CompanyMembership


class CompanyMemberApproveForm(forms.Form):
    """
    Форма подтверждения сотрудника администратором с выбором ролей.
    Используется для одобрения заявок на участие в компании.
    """

    is_manager = forms.BooleanField(
        label="Менеджер",
        required=False,
        help_text="Может работать с заявками и проектами",
    )
    is_developer = forms.BooleanField(
        label="Разработчик",
        required=False,
        help_text="Может работать с задачами в проектах",
    )

    def __init__(self, *args, **kwargs):
        self.membership = kwargs.pop("membership", None)
        super().__init__(*args, **kwargs)
        if self.membership:
            self.fields['is_manager'].initial = self.membership.is_manager
            self.fields['is_developer'].initial = self.membership.is_developer

    def clean(self):
        cleaned_data = super().clean()
        is_manager = cleaned_data.get('is_manager', False)
        is_developer = cleaned_data.get('is_developer', False)
        
        if not is_manager and not is_developer:
            raise forms.ValidationError("Необходимо выбрать хотя бы одну роль: менеджер или разработчик")
        
        return cleaned_data

    def save(self):
        """
        Обновляет роли и подтверждает участие.
        """
        if self.membership:
            self.membership.is_manager = self.cleaned_data['is_manager']
            self.membership.is_developer = self.cleaned_data['is_developer']
            self.membership.is_approved = True
            self.membership.save()
        return self.membership

