from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    TodoListCreateView, 
    TodoDetailView, 
    RegisterView, 
    CurrentUserView, 
    TeamListView, 
    UserListView, 
    UserDetailAdminView, 
    TodoAssignView, 
    TodoRespondView,
    NotificationListView,
    NotificationUnreadCountView,
    NotificationMarkReadView,
    NotificationMarkAllReadView,
    AdminDashboardView,
    AdminUserTodosView,
    AdminTodoExplorerView,
)
from .models import Todo, Team 

urlpatterns = [
    path('todos/', TodoListCreateView.as_view(), name='todo-list-create'),
    path('todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),
    path("todos/<int:pk>/assign/", TodoAssignView.as_view(), name="todo-assign"),

    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),

    path("teams/", TeamListView.as_view(), name="team-list"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailAdminView.as_view(), name="user-detail-admin"),
    path("admin/dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),
    path("admin/todos/", AdminTodoExplorerView.as_view(), name="admin-todo-explorer"),
    path("admin/users/<int:pk>/todos/", AdminUserTodosView.as_view(), name="admin-user-todos"),
    path("todos/<int:pk>/respond/", TodoRespondView.as_view(),name="todo-respond"),

    path("notifications/", NotificationListView.as_view(), name="notification-list"),
    path("notifications/unread-count/", NotificationUnreadCountView.as_view(), name="notification-unread-count"),
    path("notifications/<int:pk>/read/", NotificationMarkReadView.as_view(), name="notification-mark-read"),
    path("notifications/read-all/", NotificationMarkAllReadView.as_view(), name="notification-mark-all-read"),
]