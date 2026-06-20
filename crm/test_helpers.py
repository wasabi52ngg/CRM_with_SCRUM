from django.contrib.auth import get_user_model

from crm.models import ClientRequest, Company, CompanyMembership, Project, Task

User = get_user_model()
TEST_PHONE = "+7-900-123-45-67"
TEST_PASSWORD = "TestPass123"


def make_user(username, *, email=None, role=User.Role.MANAGER):
    return User.objects.create_user(
        username=username,
        email=email or f"{username}@test.com",
        password=TEST_PASSWORD,
        phone=TEST_PHONE,
        role=role,
    )


def make_company(slug, name=None):
    return Company.objects.create(name=name or slug, slug=slug)


def add_membership(company, user, *, is_manager=False, is_developer=False, is_owner=False):
    return CompanyMembership.objects.create(
        company=company,
        user=user,
        is_manager=is_manager,
        is_developer=is_developer,
        is_owner=is_owner,
        is_approved=True,
    )


def make_request(company, title="Test request", **kwargs):
    defaults = {
        "company": company,
        "project_type": ClientRequest.ProjectType.WEBSITE,
        "title": title,
        "contact_email": "client@test.com",
    }
    defaults.update(kwargs)
    return ClientRequest.objects.create(**defaults)


def make_project(company, name="Test project", **kwargs):
    return Project.objects.create(company=company, name=name, **kwargs)


def make_task(project, title="Test task", **kwargs):
    defaults = {
        "project": project,
        "title": title,
        "task_type": Task.TaskType.FULLSTACK,
    }
    defaults.update(kwargs)
    return Task.objects.create(**defaults)
