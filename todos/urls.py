from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import TodoListCreateView, TodoDetailView, RegisterView, CurrentUserView, TeamListView, UserListView, UserDetailAdminView
from .models import Todo, Team 

urlpatterns = [
    path('todos/', TodoListCreateView.as_view(), name='todo-list-create'),
    path('todos/<int:pk>/', TodoDetailView.as_view(), name='todo-detail'),

    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', TokenObtainPairView.as_view(), name='token-obtain-pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('auth/me/', CurrentUserView.as_view(), name='current-user'),

    path("teams/", TeamListView.as_view(), name="team-list"),
    path("users/", UserListView.as_view(), name="user-list"),
    path("users/<int:pk>/", UserDetailAdminView.as_view(), name="user-detail-admin"),
]