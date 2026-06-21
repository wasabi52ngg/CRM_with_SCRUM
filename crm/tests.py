from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from crm.models import ClientRequest, Epic, InAppNotification, Project, RequestCheckpoint, RequestCheckpointEdge, Task
from crm.test_helpers import (
    TEST_PASSWORD,
    add_membership,
    make_company,
    make_project,
    make_request,
    make_task,
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
        self.request_obj = make_request(self.company, title="Alpha request", manager=self.manager)
        self.project = make_project(
            self.company,
            name="Alpha project",
            client_request=self.request_obj,
        )

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


class AccessControlTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("beta", "Beta Dev")
        self.owner = make_user("owner", role=User.Role.MANAGER)
        self.manager_a = make_user("mgra", role=User.Role.MANAGER)
        self.manager_b = make_user("mgrb", role=User.Role.MANAGER)
        self.developer = make_user("dev2", role=User.Role.DEVELOPER)
        add_membership(self.company, self.owner, is_manager=True, is_owner=True)
        add_membership(self.company, self.manager_a, is_manager=True)
        add_membership(self.company, self.manager_b, is_manager=True)
        add_membership(self.company, self.developer, is_developer=True)
        self.request_obj = make_request(self.company, title="Beta request", manager=self.manager_a)
        self.project = make_project(
            self.company,
            name="Beta project",
            client_request=self.request_obj,
        )

    def test_manager_not_responsible_cannot_open_kanban(self):
        self.client.login(username="mgrb", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:kanban_board", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_manager_responsible_can_open_kanban(self):
        self.client.login(username="mgra", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:kanban_board", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_open_kanban(self):
        self.client.login(username="owner", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:kanban_board", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)

    def test_developer_without_tasks_cannot_open_kanban(self):
        self.client.login(username="dev2", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:kanban_board", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 302)

    def test_developer_with_assigned_task_can_open_kanban(self):
        Task.objects.create(
            project=self.project,
            title="Dev task",
            assignee=self.developer,
            task_type="fullstack",
        )
        self.client.login(username="dev2", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:kanban_board", kwargs={"pk": self.project.pk}))
        self.assertEqual(response.status_code, 200)

    def test_manager_not_responsible_sees_request_without_project_link(self):
        self.client.login(username="mgrb", password=TEST_PASSWORD)
        response = self.client.get(
            reverse("crm:manager_request_detail", kwargs={"pk": self.request_obj.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_access_project"])


class PublicRequestValidationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("valid-co", "Valid Co")

    def test_public_request_requires_personal_data_consent(self):
        response = self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "valid-co"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "Без согласия",
                "description": "Тест",
                "contact_email": "no-consent@test.com",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request.html")
        self.assertFalse(ClientRequest.objects.filter(title="Без согласия").exists())

    def test_public_request_rejects_title_too_long(self):
        response = self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "valid-co"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "x" * 256,
                "description": "Тест",
                "contact_email": "long-title@test.com",
                "personal_data_consent": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request.html")
        self.assertFalse(ClientRequest.objects.filter(contact_email="long-title@test.com").exists())
        self.assertIn("title", response.context["form"].errors)

    def test_public_request_rejects_telegram_too_long(self):
        response = self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "valid-co"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "Нормальный заголовок",
                "description": "Тест",
                "contact_email": "long-tg@test.com",
                "contact_telegram": "@" + "a" * 64,
                "personal_data_consent": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/public_request.html")
        self.assertFalse(ClientRequest.objects.filter(contact_email="long-tg@test.com").exists())
        self.assertIn("contact_telegram", response.context["form"].errors)

    def test_privacy_policy_page_opens(self):
        response = self.client.get(reverse("crm:privacy_policy"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/privacy_policy.html")


class AnonymousRequestSessionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("sess-co", "Session Co")

    def test_anonymous_request_saved_in_session_and_bound_after_login(self):
        response = self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "sess-co"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "Гостевая заявка",
                "description": "До регистрации",
                "contact_email": "guest@test.com",
                "personal_data_consent": "1",
            },
        )
        self.assertEqual(response.status_code, 200)
        req = ClientRequest.objects.get(title="Гостевая заявка")
        session = self.client.session
        session.load()
        self.assertIn(req.pk, session.get("anonymous_request_ids", []))

        client_user = make_user("guest_client", role=User.Role.CLIENT)
        self.client.login(username="guest_client", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:client_requests"))
        self.assertEqual(response.status_code, 200)
        req.refresh_from_db()
        self.assertEqual(req.client_id, client_user.id)
        session = self.client.session
        session.load()
        self.assertFalse(session.get("anonymous_request_ids"))


class ManagerWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("flow-co", "Flow Co")
        self.manager = make_user("flow_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.request_obj = make_request(self.company, title="Workflow request", manager=None)

    def test_manager_takes_request(self):
        self.client.login(username="flow_mgr", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:manager_request_detail", kwargs={"pk": self.request_obj.pk}),
            {"action": "take"},
        )
        self.assertEqual(response.status_code, 302)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.manager_id, self.manager.id)
        self.assertEqual(self.request_obj.status, ClientRequest.Status.DISCUSS)

    def test_manager_moves_request_to_work_creates_project(self):
        self.request_obj.manager = self.manager
        self.request_obj.status = ClientRequest.Status.DISCUSS
        self.request_obj.save()
        self.client.login(username="flow_mgr", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:manager_request_detail", kwargs={"pk": self.request_obj.pk}),
            {"action": "to_work"},
        )
        self.assertEqual(response.status_code, 302)
        self.request_obj.refresh_from_db()
        self.assertEqual(self.request_obj.status, ClientRequest.Status.IN_PROGRESS)
        self.assertTrue(Project.objects.filter(client_request=self.request_obj).exists())


class KanbanApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("kanban-co", "Kanban Co")
        self.manager = make_user("kanban_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.request_obj = make_request(self.company, title="Kanban request", manager=self.manager)
        self.project = make_project(self.company, name="Kanban project", client_request=self.request_obj)
        self.task = make_task(
            self.project,
            title="Move me",
            assignee=self.manager,
            status=Task.Status.TODO,
        )

    def test_kanban_move_changes_task_status(self):
        import json

        self.client.login(username="kanban_mgr", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:kanban_move"),
            data=json.dumps({"id": self.task.pk, "status": Task.Status.IN_PROGRESS}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)

    def test_kanban_move_forbidden_for_unassigned_developer(self):
        import json

        developer = make_user("kanban_dev", role=User.Role.DEVELOPER)
        add_membership(self.company, developer, is_developer=True)
        self.client.login(username="kanban_dev", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:kanban_move"),
            data=json.dumps({"id": self.task.pk, "status": Task.Status.IN_PROGRESS}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)


class KanbanEpicFilterTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("epic-co", "Epic Co")
        self.manager = make_user("epic_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.request_obj = make_request(self.company, title="Epic request", manager=self.manager)
        self.project = make_project(self.company, name="Epic project", client_request=self.request_obj)
        self.epic = Epic.objects.create(project=self.project, title="Auth epic", order=1)
        self.task_with_epic = make_task(
            self.project,
            title="Task in epic",
            epic=self.epic,
            status=Task.Status.TODO,
        )
        self.task_without_epic = make_task(
            self.project,
            title="Task without epic",
            status=Task.Status.TODO,
        )
        self.client.login(username="epic_mgr", password=TEST_PASSWORD)
        self.kanban_url = reverse("crm:kanban_board", kwargs={"pk": self.project.pk})

    def test_kanban_shows_all_tasks_without_epic_filter(self):
        response = self.client.get(self.kanban_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task in epic")
        self.assertContains(response, "Task without epic")
        self.assertEqual(response.context["epic_filter_mode"], "all")

    def test_kanban_epic_none_shows_only_tasks_without_epic(self):
        response = self.client.get(f"{self.kanban_url}?epic=none")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Task in epic")
        self.assertContains(response, "Task without epic")
        self.assertEqual(response.context["epic_filter_mode"], "none")

    def test_kanban_epic_id_shows_only_matching_tasks(self):
        response = self.client.get(f"{self.kanban_url}?epic={self.epic.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Task in epic")
        self.assertNotContains(response, "Task without epic")
        self.assertEqual(response.context["epic_filter_id"], self.epic.pk)

    def test_kanban_invalid_epic_param_redirects_to_all_tasks(self):
        response = self.client.get(f"{self.kanban_url}?epic=99999")
        self.assertEqual(response.status_code, 302)
        self.assertNotIn("epic=", response.url)


class TaskPanelApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("panel-co", "Panel Co")
        self.manager = make_user("panel_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.project = make_project(self.company, name="Panel project")
        self.task = make_task(self.project, title="Panel task", assignee=self.manager)

    def test_task_panel_detail_returns_checkpoints(self):
        import json

        self.client.login(username="panel_mgr", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:task_panel_api", kwargs={"pk": self.task.pk}),
            data=json.dumps({"action": "detail"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["task"]["id"], self.task.pk)
        self.assertIn("checkpoints", data)

    def test_task_panel_checkpoint_create_and_update(self):
        import json

        self.client.login(username="panel_mgr", password=TEST_PASSWORD)
        create_resp = self.client.post(
            reverse("crm:task_panel_api", kwargs={"pk": self.task.pk}),
            data=json.dumps({"action": "checkpoint_create", "title": "Шаг 1", "comment": ""}),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 200)
        cp_id = create_resp.json()["checkpoint"]["id"]
        update_resp = self.client.post(
            reverse("crm:task_panel_api", kwargs={"pk": self.task.pk}),
            data=json.dumps({"action": "checkpoint_update", "id": cp_id, "is_done": True}),
            content_type="application/json",
        )
        self.assertEqual(update_resp.status_code, 200)
        self.assertTrue(update_resp.json()["ok"])
        cp = self.task.checkpoints.get(pk=cp_id)
        self.assertTrue(cp.is_done)


class DeveloperWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("dev-co", "Dev Co")
        self.manager = make_user("dev_mgr", role=User.Role.MANAGER)
        self.developer = make_user("dev_worker", role=User.Role.DEVELOPER)
        add_membership(self.company, self.manager, is_manager=True)
        add_membership(self.company, self.developer, is_developer=True)
        self.project = make_project(self.company, name="Dev project")
        self.task = make_task(self.project, title="Open task", status=Task.Status.TODO)

    def test_developer_takes_open_task(self):
        self.client.login(username="dev_worker", password=TEST_PASSWORD)
        response = self.client.post(reverse("crm:dev_take_task", kwargs={"pk": self.task.pk}))
        self.assertEqual(response.status_code, 302)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee_id, self.developer.id)
        self.assertEqual(self.task.status, Task.Status.IN_PROGRESS)


class RequestCheckpointApiTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("cp-co", "Checkpoint Co")
        self.manager = make_user("cp_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)
        self.request_obj = make_request(self.company, title="Checkpoint request", manager=self.manager)

    def test_request_checkpoint_create_via_api(self):
        import json

        self.client.login(username="cp_mgr", password=TEST_PASSWORD)
        response = self.client.post(
            reverse("crm:manager_request_checkpoints_api", kwargs={"pk": self.request_obj.pk}),
            data=json.dumps({"action": "create", "title": "Согласование ТЗ", "comment": "Этап 1"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertTrue(
            RequestCheckpoint.objects.filter(request=self.request_obj, title="Согласование ТЗ").exists()
        )

    def test_request_checkpoint_edge_create_and_delete_via_api(self):
        import json

        self.client.login(username="cp_mgr", password=TEST_PASSWORD)
        cp1 = RequestCheckpoint.objects.create(
            request=self.request_obj, title="Этап A", order=1, x=0, y=0
        )
        cp2 = RequestCheckpoint.objects.create(
            request=self.request_obj, title="Этап B", order=2, x=240, y=0
        )
        create_resp = self.client.post(
            reverse("crm:manager_request_checkpoints_api", kwargs={"pk": self.request_obj.pk}),
            data=json.dumps({"action": "edge_create", "source_id": cp1.id, "target_id": cp2.id}),
            content_type="application/json",
        )
        self.assertEqual(create_resp.status_code, 200)
        edge_id = create_resp.json()["edge"]["id"]
        self.assertTrue(
            RequestCheckpointEdge.objects.filter(
                request=self.request_obj, source=cp1, target=cp2
            ).exists()
        )
        delete_resp = self.client.post(
            reverse("crm:manager_request_checkpoints_api", kwargs={"pk": self.request_obj.pk}),
            data=json.dumps({"action": "edge_delete", "id": edge_id}),
            content_type="application/json",
        )
        self.assertEqual(delete_resp.status_code, 200)
        self.assertTrue(delete_resp.json()["ok"])
        self.assertFalse(RequestCheckpointEdge.objects.filter(pk=edge_id).exists())


class NotificationWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("note-co", "Notify Co")
        self.manager = make_user("note_mgr", role=User.Role.MANAGER)
        add_membership(self.company, self.manager, is_manager=True)

    def test_new_public_request_notifies_manager(self):
        self.client.post(
            reverse("crm:public_request_by_slug", kwargs={"company_slug": "note-co"}),
            {
                "project_type": ClientRequest.ProjectType.WEBSITE,
                "title": "Уведомление менеджеру",
                "description": "Тест",
                "contact_email": "notify@test.com",
                "personal_data_consent": "1",
            },
        )
        self.assertTrue(
            InAppNotification.objects.filter(
                user=self.manager,
                kind=InAppNotification.Kind.NEW_CLIENT_REQUEST,
            ).exists()
        )

    def test_notifications_api_marks_unread_count(self):
        InAppNotification.objects.create(
            user=self.manager,
            kind=InAppNotification.Kind.TASK_UPDATED,
            title="Изменение задачи",
            body="Тест",
        )
        self.client.login(username="note_mgr", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:notifications_api"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(data.get("unread_count", 0), 1)


class InternalDocsAccessTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.company = make_company("docs-co", "Docs Co")
        self.manager = make_user("docs_mgr", role=User.Role.MANAGER)
        self.client_user = make_user("docs_client", role=User.Role.CLIENT)
        add_membership(self.company, self.manager, is_manager=True)

    def test_manager_can_open_scrum_glossary(self):
        self.client.login(username="docs_mgr", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:scrum_glossary"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "crm/scrum_glossary.html")

    def test_client_redirected_from_scrum_glossary(self):
        self.client.login(username="docs_client", password=TEST_PASSWORD)
        response = self.client.get(reverse("crm:scrum_glossary"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("client/requests", response.url)
