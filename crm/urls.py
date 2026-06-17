from django.urls import path

from .views import (
    PublicRequestChooseCompanyView,
    PublicRequestView,
    PrivacyPolicyView,
    ManagerRequestListView,
    ManagerRequestDetailView,
    ManagerProjectDetailView,
    DeveloperOpenTasksView,
    DeveloperTakeTaskView,
    DashboardView,
    KanbanBoardView,
    KanbanMoveApiView,
    KanbanCreateTaskApiView,
    TaskPanelApiView,
    ScrumApiView,
    ScrumReportsView,
    ScrumGlossaryView,
    NotificationsApiView,
    LandingView,
    ClientRequestListView,
    ClientRequestDetailView,
    ClientRequestBySessionView,
    ClientCreateRequestView,
    RequestCheckpointApiView,
    CompanyListView,
    CompanyDetailView,
    CompanyReviewsView,
)


app_name = "crm"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("privacy/", PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("request/", PublicRequestChooseCompanyView.as_view(), name="public_request_choose_company"),
    path("request/<slug:company_slug>/", PublicRequestView.as_view(), name="public_request_by_slug"),
    path("r/<str:token>/", PublicRequestView.as_view(), name="public_request_by_token"),
    path("client/requests/", ClientRequestListView.as_view(), name="client_requests"),
    path("client/requests/new/", ClientCreateRequestView.as_view(), name="client_request_create"),
    path("client/requests/<int:pk>/", ClientRequestDetailView.as_view(), name="client_request_detail"),
    path("client/request/session/<int:pk>/", ClientRequestBySessionView.as_view(), name="client_request_by_session"),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("help/scrum/", ScrumGlossaryView.as_view(), name="scrum_glossary"),
    path("notifications/api/", NotificationsApiView.as_view(), name="notifications_api"),
    path("manager/requests/", ManagerRequestListView.as_view(), name="manager_request_list"),
    path("manager/requests/<int:pk>/", ManagerRequestDetailView.as_view(), name="manager_request_detail"),
    path(
        "manager/requests/<int:pk>/checkpoints/",
        RequestCheckpointApiView.as_view(),
        name="manager_request_checkpoints_api",
    ),
    path("manager/projects/<int:pk>/", ManagerProjectDetailView.as_view(), name="manager_project_detail"),
    path("manager/projects/<int:pk>/board/", KanbanBoardView.as_view(), name="kanban_board"),
    path("manager/projects/<int:pk>/reports/", ScrumReportsView.as_view(), name="scrum_reports"),
    path("manager/tasks/<int:pk>/panel/", TaskPanelApiView.as_view(), name="task_panel_api"),
    path("scrum/api/", ScrumApiView.as_view(), name="scrum_api"),
    path("kanban/move/", KanbanMoveApiView.as_view(), name="kanban_move"),
    path("kanban/create/", KanbanCreateTaskApiView.as_view(), name="kanban_create_task"),
    path("dev/open/", DeveloperOpenTasksView.as_view(), name="dev_open_tasks"),
    path("dev/take/<int:pk>/", DeveloperTakeTaskView.as_view(), name="dev_take_task"),
    path("companies/", CompanyListView.as_view(), name="company_list"),
    path("companies/<slug:slug>/reviews/", CompanyReviewsView.as_view(), name="company_reviews"),
    path("companies/<slug:slug>/", CompanyDetailView.as_view(), name="company_detail"),
]


