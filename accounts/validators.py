import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_phone_number(value):
    phone_regex = re.compile(r'^\+\d-\d{3}-\d{3}-\d{2}-\d{2}$')
    if not phone_regex.match(value):
        raise ValidationError(
            _('Неверный формат номера телефона. Используйте формат "+#-###-###-##-##".'),
            params={'value': value},
        )


def validate_email(value):
    email_regex = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
    if not email_regex.match(value):
        raise ValidationError(
            _('Неверный формат email. Используйте формат "username@domain.com".'),
            params={'value': value},
        )

