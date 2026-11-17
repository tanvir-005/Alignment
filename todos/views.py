from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from drf_spectacular.utils import extend_schema

from .models import Todo, Team, UserProfile, Notification
from .serializers import TodoSerializer, TeamSerializer, UserListSerializer, UserAdminUpdateSerializer, TodoAssignmentSerializer, TodoAssignmentResponseSerializer, NotificationSerializer  
from .pagination import TodoPagination, PaginatedTodoSerializer
from .auth_serializers import RegisterSerializer
from .schema_serializers import RegisterResponseSerializer

class TodoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id='todo_list',
        responses=PaginatedTodoSerializer
    )
    def get(self, request):
        todos = Todo.objects.filter(
            Q(user=request.user) | Q(assignee=request.user)
        ).select_related(
            "user", "assignee", "team"
        ).distinct()

        # Filter by task status
        todo_status = request.query_params.get('status')

        status_mapping = {
            "pending": Todo.TaskStatus.PENDING,
            "in_progress": Todo.TaskStatus.IN_PROGRESS,
            "completed": Todo.TaskStatus.COMPLETED,
        }

        if todo_status is not None:
            if todo_status not in status_mapping:
                return Response(
                    {
                        "error": (
                            "Invalid status parameter. "
                            "Must be pending, in_progress, or completed."
                        ),
                        "code": status.HTTP_400_BAD_REQUEST
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            todos = todos.filter(
                task_status=status_mapping[todo_status]
            )

        # Search TODOs by title
        search_query = request.query_params.get('search')

        if search_query:
            todos = todos.filter(
                title__icontains=search_query.strip()
            )

        # Sorting
        sort_by = request.query_params.get('sort_by', 'created_at')
        order = request.query_params.get('order', 'desc')

        allowed_sort_fields = ['created_at', 'title']
        allowed_orders = ['asc', 'desc']

        if sort_by not in allowed_sort_fields:
            return Response(
                {
                    "error": (
                        "Invalid sorting field. "
                        "Allowed values: created_at, title."
                    ),
                    "code": status.HTTP_400_BAD_REQUEST
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        if order not in allowed_orders:
            return Response(
                {
                    "error": (
                        "Invalid sorting order. "
                        "Allowed values: asc, desc."
                    ),
                    "code": status.HTTP_400_BAD_REQUEST
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        ordering = sort_by if order == 'asc' else f'-{sort_by}'
        todos = todos.order_by(ordering, '-id')

        # Pagination
        paginator = TodoPagination()
        paginated_todos = paginator.paginate_queryset(todos, request)

        serializer = TodoSerializer(paginated_todos, many=True)

        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        request=TodoSerializer,
        responses={201: TodoSerializer}
    )
    def post(self, request):
        serializer = TodoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        serializer.save(
            user=request.user,
            team=request.user.profile.team
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )


class TodoDetailView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = TodoSerializer

    def get_object(self, pk):
        return get_object_or_404(
            Todo.objects.select_related(
                "user", "assignee", "team"
            ).filter(
                Q(user=self.request.user)
                | Q(assignee=self.request.user)
            ),
            pk=pk
        )

    def can_edit(self, todo, user):
        if todo.assignee_id is None:
            return todo.user_id == user.id

        return todo.assignee_id == user.id

    def get(self, request, pk):
        todo = self.get_object(pk)
        serializer = TodoSerializer(todo)

        return Response(serializer.data)

    def put(self, request, pk):
        todo = self.get_object(pk)

        if not self.can_edit(todo, request.user):
            return Response(
                {"error": "You do not have permission to edit this todo."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TodoSerializer(todo, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def patch(self, request, pk):
        todo = self.get_object(pk)

        if not self.can_edit(todo, request.user):
            return Response(
                {"error": "You do not have permission to edit this todo."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TodoSerializer(
            todo,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def delete(self, request, pk):
        todo = self.get_object(pk)

        if todo.assignee_id is not None or todo.user_id != request.user.id:
            return Response(
                {"error": "You do not have permission to delete this todo."},
                status=status.HTTP_403_FORBIDDEN
            )

        todo.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(
        operation_id='register_user',
        request=RegisterSerializer,
        responses={201: RegisterResponseSerializer}
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": "User registered successfully.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                }
            },
            status=status.HTTP_201_CREATED
        )

class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        profile = user.profile

        team = None
        if profile.team:
            team = {
                "id": profile.team.id,
                "name": profile.team.name,
            }

        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": profile.role,
            "team": team,
        })

class TeamListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        teams = Team.objects.prefetch_related(
            "members__user"
        ).all()

        serializer = TeamSerializer(teams, many=True)
        return Response(serializer.data)

class IsAdminUserRole:
    def has_permission(self, request, view):
        return (
            request.user
            and request.user.is_authenticated
            and request.user.profile.role == "ADMIN"
        )

class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        users = User.objects.select_related(
            "profile__team"
        ).all().order_by("id")

        serializer = UserListSerializer(users, many=True)
        return Response(serializer.data)

class UserDetailAdminView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def patch(self, request, pk):
        user = get_object_or_404(
            User.objects.select_related("profile"),
            pk=pk
        )

        serializer = UserAdminUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updates = serializer.validated_data
        profile = user.profile

        if "role" in updates:
            new_role = updates["role"]

            if user.id == request.user.id:
                return Response(
                    {"error": "You cannot change your own role."},
                    status=status.HTTP_403_FORBIDDEN
                )

            if (
                profile.role == UserProfile.Role.ADMIN
                and new_role == UserProfile.Role.MEMBER
            ):
                admin_count = UserProfile.objects.filter(
                    role=UserProfile.Role.ADMIN
                ).count()

                if admin_count <= 1:
                    return Response(
                        {"error": "Cannot demote the last admin."},
                        status=status.HTTP_409_CONFLICT
                    )

            profile.role = new_role

        if "team" in updates:
            profile.team = updates["team"]

        profile.save()

        return Response(UserListSerializer(user).data)

class TodoAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        todo = get_object_or_404(Todo, pk=pk)

        if todo.user_id != request.user.id:
            return Response(
                {"error": "Only the creator can assign this todo."},
                status=status.HTTP_403_FORBIDDEN
            )

        if todo.assignee_id is not None:
            return Response(
                {"error": "This todo is already assigned."},
                status=status.HTTP_409_CONFLICT
            )

        serializer = TodoAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignee = serializer.validated_data["assignee"]

        if assignee.id == request.user.id:
            return Response(
                {"error": "You cannot assign a todo to yourself."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (
            todo.team_id is None
            or assignee.profile.team_id != todo.team_id
        ):
            return Response(
                {"error": "Assignee must belong to the same team."},
                status=status.HTTP_400_BAD_REQUEST
            )

        todo.assignee = assignee
        todo.assignment_status = Todo.AssignmentStatus.PENDING
        todo.save(update_fields=["assignee", "assignment_status", "updated_at"])

        Notification.objects.create(
            recipient=assignee,
            actor=request.user,
            todo=todo,
            message=f"{request.user.username} assigned you a todo: {todo.title}",
        )

        return Response(
            TodoSerializer(todo).data,
            status=status.HTTP_200_OK
        )

class TodoRespondView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, pk):
        todo = get_object_or_404(
            Todo.objects.select_for_update(),
            pk=pk,
        )

        if todo.assignee_id != request.user.id:
            return Response(
                {"detail": "Only the assigned user can respond."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if todo.assignment_status != Todo.AssignmentStatus.PENDING:
            return Response(
                {"detail": "This assignment is no longer pending."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = TodoAssignmentResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        decision = serializer.validated_data["decision"]

        todo.assignment_status = decision
        todo.save(update_fields=["assignment_status", "updated_at"])

        Notification.objects.create(
            recipient=todo.user,
            actor=request.user,
            todo=todo,
            message=(
                f"{request.user.username} "
                f"{decision.lower()} your assignment: {todo.title}"
            ),
        )

        return Response(TodoSerializer(todo).data)

class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related("actor", "todo")

        serializer = NotificationSerializer(
            notifications,
            many=True,
        )

        return Response(serializer.data)


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).count()

        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        notification = get_object_or_404(
            Notification,
            pk=pk,
            recipient=request.user,
        )

        notification.is_read = True
        notification.save(update_fields=["is_read"])

        return Response({"detail": "Notification marked as read."})


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        updated_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        ).update(is_read=True)

        return Response({
            "detail": "All notifications marked as read.",
            "updated_count": updated_count,
        })