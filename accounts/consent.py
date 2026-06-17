from django import forms

CONSENT_REQUIRED_MESSAGE = (
    'Необходимо дать согласие на обработку персональных данных'
)


class PersonalDataConsentMixin(forms.Form):
    """Обязательное согласие на обработку ПДн (152-ФЗ) при регистрации."""

    personal_data_consent = forms.BooleanField(
        label='',
        required=True,
        error_messages={'required': CONSENT_REQUIRED_MESSAGE},
    )


def mark_personal_data_consent(user):
    from django.utils import timezone

    user.personal_data_consent_at = timezone.now()
    user.save(update_fields=['personal_data_consent_at'])
