from django import forms
from django.contrib.auth import get_user_model

from accounts.consent import PersonalDataConsentMixin
from .models import ClientRequest, CompanyMembership


class ClientRequestForm(PersonalDataConsentMixin, forms.ModelForm):
    """Поля заявки клиента с ограничениями длины как в модели и согласием на ПДн."""

    class Meta:
        model = ClientRequest
        fields = ("project_type", "title", "contact_email", "contact_telegram", "description")
        widgets = {
            "project_type": forms.Select(),
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Краткое описание проекта",
                    "maxlength": "255",
                }
            ),
            "contact_email": forms.EmailInput(attrs={"placeholder": "your@email.com"}),
            "contact_telegram": forms.TextInput(
                attrs={
                    "placeholder": "@username",
                    "maxlength": "64",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "rows": 6,
                    "placeholder": (
                        "Опишите детали вашего проекта, требования, сроки "
                        "и другую важную информацию..."
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project_type"].empty_label = "Выберите тип проекта"
        self.fields["title"].required = True
        self.fields["contact_email"].required = True
        self.fields["contact_telegram"].required = False
        self.fields["description"].required = False

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

