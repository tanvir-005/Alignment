from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # auth
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/login/", views.LoginView.as_view(), name="token-obtain-pair"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/me/", views.CurrentUserView.as_view(), name="current-user"),

    # teams (admin manages; members read their own)
    path("teams/", views.TeamListCreateView.as_view(), name="team-list"),
    path("teams/<int:pk>/", views.TeamDetailView.as_view(), name="team-detail"),
    path("teams/<int:pk>/members/", views.TeamMembersView.as_view(), name="team-members"),
    path(
        "teams/<int:pk>/members/<int:user_id>/",
        views.TeamMemberDetailView.as_view(),
        name="team-member-detail",
    ),
    path(
        "teams/<int:pk>/members/<int:user_id>/impact/",
        views.TeamMemberImpactView.as_view(),
        name="team-member-impact",
    ),
    path("teams/<int:pk>/replace-pm/", views.TeamReplacePMView.as_view(), name="team-replace-pm"),

    # users (admin)
    path("users/", views.UserListView.as_view(), name="user-list"),
    path(
        "users/<int:pk>/deactivate/",
        views.UserActivationView.as_view(activate=False),
        name="user-deactivate",
    ),
    path(
        "users/<int:pk>/activate/",
        views.UserActivationView.as_view(activate=True),
        name="user-activate",
    ),

    # todos
    path("todos/", views.TodoListCreateView.as_view(), name="todo-list-create"),
    path("todos/<int:pk>/", views.TodoDetailView.as_view(), name="todo-detail"),
    path("todos/<int:pk>/status/", views.TodoStatusView.as_view(), name="todo-status"),
    path("todos/<int:pk>/activities/", views.TodoActivityListView.as_view(), name="todo-activities"),

    # notifications
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),
    path(
        "notifications/unread-count/",
        views.NotificationUnreadCountView.as_view(),
        name="notification-unread-count",
    ),
    path(
        "notifications/read-all/",
        views.NotificationMarkAllReadView.as_view(),
        name="notification-mark-all-read",
    ),
    path(
        "notifications/<int:pk>/read/",
        views.NotificationMarkReadView.as_view(),
        name="notification-mark-read",
    ),

    # admin overview
    path("admin/overview/", views.AdminOverviewView.as_view(), name="admin-overview"),
]
