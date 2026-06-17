from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from crm.models import ClientRequest
from crm.test_helpers import (
    TEST_PASSWORD,
    add_membership,
    make_company,
    make_project,
    make_request,
    make_user,
)

User = get_user_model()


class PublicPagesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("acme", "Acme IT")

    def test_landing_opens_for_guest(self):
        response = self.client.get(reverse("crm:landing"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/landing.html")

    def test_choose_company_page_opens(self):
        response = self.client.get(reverse("crm:public_request_choose_company"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request_choose_company.html")

    def test_public_request_form_opens(self):
        response = self.client.get(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "acme"})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request.html")

    def test_public_request_form_creates_request(self):
        response = self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "acme"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "Нужен сайт",
                "description": "Корпоративный сайт",
                "contact_email": "new@client.com",
                "personal_data_consent": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request_success.html")
        self.assertTrue(ClientRequest.objects.filter(title="Нужен сайт").exists())


class AuthenticatedPagesTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("alpha", "Alpha Dev")
        self.manager = make_user("mgr", role=User.Role.MANAGER)
        self.developer = make_user("dev", role=User.Role.DEVELOPER)
        add_membership(self.company, self.manager, is_manager=True)
        add_membership(self.company, self.developer, is_developer=True)
        self.request_obj = make_request(self.company, title="Alpha request")
        self.project = make_project(self.company, name="Alpha project")

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse("crm:dashboard"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_manager_dashboard_opens(self):
        self.client.login(username="mgr", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/dashboard_manager.html")

    def test_manager_request_list_opens(self):
        self.client.login(username="mgr", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:manager_request_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/manager/request_list.html")
        titles = [r.title for r in response.context["object_list"]]
        self.assertIn("Alpha request", titles)

    def test_manager_request_detail_opens(self):
        self.client.login(username="mgr", password=TEST_PASSWORD)
        response = self.client.get(
            reverse("crm:manager_request_detail", kwargs={"pk": self.request_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/manager/request_detail.html")

    def test_kanban_board_opens(self):
        self.client.login(username="mgr", password=TEST_PASSWORD)
        response = self.client.get(
            reverse("crm:kanban_board", kwargs={"pk": self.project.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/kanban.html")

    def test_developer_open_tasks_opens(self):
        self.client.login(username="dev", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:dev_open_tasks"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/dev/open_tasks.html")

    def test_notifications_api_returns_json(self):
        self.client.login(username="mgr", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:notifications_api"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ok"], True)
