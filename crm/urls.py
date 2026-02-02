from django.urls import path

from .views import (
    PublicRequestView,
    ManagerRequestListView,
    ManagerRequestDetailView,
    ManagerProjectDetailView,
    DeveloperOpenTasksView,
    DeveloperTakeTaskView,
    DashboardRedirectView,
    KanbanBoardView,
    KanbanMoveApiView,
    TaskPanelApiView,
    LandingView,
    ClientRequestListView,
    ClientRequestDetailView,
    RequestCheckpointApiView,
)


app_name = "crm"

urlpatterns = [
    path("", LandingView.as_view(), name="landing"),
    path("request/", PublicRequestView.as_view(), name="public_request"),
    # Client portal
    path("client/requests/", ClientRequestListView.as_view(), name="client_requests"),
    path("client/requests/<int:pk>/", ClientRequestDetailView.as_view(), name="client_request_detail"),
    path("dashboard/", DashboardRedirectView.as_view(), name="dashboard"),
    # Manager area
    path("manager/requests/", ManagerRequestListView.as_view(), name="manager_request_list"),
    path("manager/requests/<int:pk>/", ManagerRequestDetailView.as_view(), name="manager_request_detail"),
    path(
        "manager/requests/<int:pk>/checkpoints/",
        RequestCheckpointApiView.as_view(),
        name="manager_request_checkpoints_api",
    ),
    path("manager/projects/<int:pk>/", ManagerProjectDetailView.as_view(), name="manager_project_detail"),
    path("manager/projects/<int:pk>/board/", KanbanBoardView.as_view(), name="kanban_board"),
    path("manager/tasks/<int:pk>/panel/", TaskPanelApiView.as_view(), name="task_panel_api"),
    path("kanban/move/", KanbanMoveApiView.as_view(), name="kanban_move"),
    # Developer area
    path("dev/open/", DeveloperOpenTasksView.as_view(), name="dev_open_tasks"),
    path("dev/take/<int:pk>/", DeveloperTakeTaskView.as_view(), name="dev_take_task"),
]


