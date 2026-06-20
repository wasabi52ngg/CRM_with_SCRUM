from django.contrib.auth import get_user_model
from django.test import TestCase

from crm.models import ClientRequest, InAppNotification, Project, Task
from crm.test_helpers import (
    add_membership,
    make_company,
    make_project,
    make_request,
    make_task,
    make_user,
)

User = get_user_model()


class TaskModelTests(TestCase):
    def setUp(self):
        self.company = make_company("models-co", "Models Co")
        self.project = make_project(self.company, name="Model project", issue_key_prefix="MDL")

    def test_issue_key_assigned_on_create(self):
        task = make_task(self.project, title="First")
        self.assertEqual(task.issue_number, 1)
        self.assertEqual(task.issue_key, "MDL-1")

    def test_issue_numbers_increment_per_project(self):
        first = make_task(self.project, title="One")
        second = make_task(self.project, title="Two")
        self.assertEqual(first.issue_key, "MDL-1")
        self.assertEqual(second.issue_key, "MDL-2")

    def test_task_str_contains_type_and_title(self):
        task = make_task(self.project, title="API endpoint")
        self.assertIn("API endpoint", str(task))


class ProjectFromRequestTests(TestCase):
    def setUp(self):
        self.company = make_company("proj-co", "Proj Co")
        self.manager = make_user("pm", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.request_obj = make_request(
            self.company,
            title="Mobile app",
            manager=self.manager,
            status=ClientRequest.Status.IN_PROGRESS,
        )

    def test_project_links_back_to_client_request(self):
        project = make_project(
            self.company,
            name=self.request_obj.title,
            client_request=self.request_obj,
        )
        self.assertEqual(project.client_request_id, self.request_obj.pk)
        self.assertEqual(project.company_id, self.company.pk)


class NotificationModelTests(TestCase):
    def test_notification_str(self):
        user = make_user("notify_user", role=User.Role.MANAGER)
        note = InAppNotification.objects.create(
            user=user,
            kind=InAppNotification.Kind.NEW_CLIENT_REQUEST,
            title="Новая заявка",
            body="client@test.com",
        )
        self.assertIn(str(user.id), str(note))
