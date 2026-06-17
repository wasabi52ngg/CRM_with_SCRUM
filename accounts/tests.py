from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from crm.test_helpers import TEST_PASSWORD, make_user

User = get_user_model()


class AuthFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = make_user("auth_user", role=User.Role.CLIENT)

    def test_login_page_opens(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_logged_in_user_reaches_app(self):
        logged_in = self.client.login(username="auth_user", password=TEST_PASSWORD)
        self.assertTrue(logged_in)
        response = self.client.get(reverse("crm:dashboard"))
        self.assertEqual(response.status_code, 302)
        response = self.client.get(reverse("crm:client_requests"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/client/requests.html")
