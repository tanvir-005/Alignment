from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Count, Max
from django.utils import timezone
from datetime import timedelta

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
        if request.user.profile.role == UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Administrators have read-only todo access."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        visibility = Q(user=self.request.user) | Q(assignee=self.request.user)
        if self.request.user.profile.role == UserProfile.Role.ADMIN:
            visibility = Q()

        return get_object_or_404(
            Todo.objects.select_related(
                "user", "assignee", "team"
            ).filter(visibility),
            pk=pk
        )

    def can_edit(self, todo, user):
        if user.profile.role == UserProfile.Role.ADMIN:
            return False

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

        if (
            request.user.profile.role == UserProfile.Role.ADMIN
            or todo.assignee_id is not None
            or todo.user_id != request.user.id
        ):
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
        ).annotate(
            created_todo_count=Count("todos", distinct=True),
            assigned_todo_count=Count("assigned_todos", distinct=True),
        ).order_by("id")

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

        user = User.objects.select_related(
            "profile__team"
        ).annotate(
            created_todo_count=Count("todos", distinct=True),
            assigned_todo_count=Count("assigned_todos", distinct=True),
        ).get(pk=user.pk)

        return Response(UserListSerializer(user).data)

class TodoAssignView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.profile.role == UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Administrators have read-only todo access."},
                status=status.HTTP_403_FORBIDDEN,
            )

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
        if request.user.profile.role == UserProfile.Role.ADMIN:
            return Response(
                {"detail": "Administrators have read-only todo access."},
                status=status.HTTP_403_FORBIDDEN,
            )

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

class TodoStatusUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def patch(self, request, pk):
        todo = get_object_or_404(
            Todo.objects.select_for_update(),
            pk=pk,
        )

        # Administrators have read-only access.
        if request.user.profile.role == UserProfile.Role.ADMIN:
            return Response(
                {
                    "detail": (
                        "Administrators have read-only access to todos."
                    )
                },
                status=status.HTTP_403_FORBIDDEN,
            )

        # Unassigned tasks can only be moved by their creator.
        if todo.assignee_id is None:
            if todo.user_id != request.user.id:
                return Response(
                    {"detail": "You cannot update this todo."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # Assigned tasks can only be moved by the accepted assignee.
        else:
            if todo.assignee_id != request.user.id:
                return Response(
                    {
                        "detail": (
                            "Only the assigned user can update this todo."
                        )
                    },
                    status=status.HTTP_403_FORBIDDEN,
                )

            if todo.assignment_status != Todo.AssignmentStatus.ACCEPTED:
                return Response(
                    {
                        "detail": (
                            "You must accept the assignment "
                            "before changing its status."
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        new_status = request.data.get("task_status")

        # Only allow moving one step left or right.
        allowed_transitions = {
            Todo.TaskStatus.PENDING: [
                Todo.TaskStatus.IN_PROGRESS,
            ],
            Todo.TaskStatus.IN_PROGRESS: [
                Todo.TaskStatus.PENDING,
                Todo.TaskStatus.COMPLETED,
            ],
            Todo.TaskStatus.COMPLETED: [
                Todo.TaskStatus.IN_PROGRESS,
            ],
        }

        if new_status not in allowed_transitions.get(todo.task_status, []):
            return Response(
                {
                    "detail": "Invalid status transition.",
                    "current_status": todo.task_status,
                    "allowed_statuses": allowed_transitions.get(
                        todo.task_status, []
                    ),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        todo.task_status = new_status
        todo.is_completed = (
            new_status == Todo.TaskStatus.COMPLETED
        )

        todo.save(
            update_fields=[
                "task_status",
                "is_completed",
                "updated_at",
            ]
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

class AdminDashboardView(APIView):
    """Workspace-wide, read-only statistics for administrators."""

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        users = User.objects.select_related("profile__team").order_by("username")
        todos = Todo.objects.select_related("team", "user", "assignee")
        total_todos = todos.count()
        completed_todos = todos.filter(
            task_status=Todo.TaskStatus.COMPLETED
        ).count()
        incomplete_todos = total_todos - completed_todos
        pending_assignments = todos.filter(
            assignment_status=Todo.AssignmentStatus.PENDING
        ).count()

        user_activity = []
        for user in users:
            assigned = Todo.objects.filter(assignee=user)
            assigned_count = assigned.count()
            completed_count = assigned.filter(
                task_status=Todo.TaskStatus.COMPLETED
            ).count()
            created_count = Todo.objects.filter(user=user).count()
            last_task_activity = Todo.objects.filter(
                Q(user=user) | Q(assignee=user)
            ).aggregate(last_activity=Max("updated_at"))["last_activity"]
            inactivity_cutoff = timezone.now() - timedelta(days=30)
            user_activity.append({
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "role": user.profile.role,
                "team": user.profile.team.name if user.profile.team else None,
                "assigned_todos": assigned_count,
                "created_todos": created_count,
                "completed_todos": completed_count,
                "pending_todos": assigned.filter(
                    task_status=Todo.TaskStatus.PENDING
                ).count(),
                "in_progress_todos": assigned.filter(
                    task_status=Todo.TaskStatus.IN_PROGRESS
                ).count(),
                "completion_rate": round(
                    completed_count / assigned_count * 100
                ) if assigned_count else 0,
                "last_login": user.last_login,
                "last_task_activity": last_task_activity,
                "inactive_30_days": (
                    last_task_activity is None
                    or last_task_activity < inactivity_cutoff
                ),
            })

        team_activity = []
        for team in Team.objects.order_by("name"):
            team_todos = todos.filter(team=team)
            team_total = team_todos.count()
            team_completed = team_todos.filter(
                task_status=Todo.TaskStatus.COMPLETED
            ).count()
            team_member_count = team.members.count()
            active_todos = team_todos.exclude(
                task_status=Todo.TaskStatus.COMPLETED
            ).count()
            team_activity.append({
                "id": team.id,
                "name": team.name,
                "members": team_member_count,
                "todos": team_total,
                "active_todos": active_todos,
                "active_todos_per_member": round(
                    active_todos / team_member_count, 1
                ) if team_member_count else 0,
                "completed_todos": team_completed,
                "incomplete_todos": team_total - team_completed,
                "completion_rate": round(
                    team_completed / team_total * 100
                ) if team_total else 0,
            })

        stale_cutoff = timezone.now() - timedelta(days=7)
        stale_todos = todos.exclude(
            task_status=Todo.TaskStatus.COMPLETED
        ).filter(updated_at__lt=stale_cutoff).order_by("updated_at")[:10]
        attention = {
            "unassigned_todos": todos.filter(assignee__isnull=True).exclude(
                task_status=Todo.TaskStatus.COMPLETED
            ).count(),
            "stale_todos": todos.exclude(
                task_status=Todo.TaskStatus.COMPLETED
            ).filter(updated_at__lt=stale_cutoff).count(),
            "inactive_users": sum(1 for item in user_activity if item["inactive_30_days"]),
            "stale_todo_preview": [{
                "id": todo.id,
                "title": todo.title,
                "team": todo.team.name if todo.team else None,
                "creator": todo.user.username,
                "assignee": todo.assignee.username if todo.assignee else None,
                "task_status": todo.task_status,
                "updated_at": todo.updated_at,
            } for todo in stale_todos],
        }

        recent_activity = [{
            "id": notification.id,
            "message": notification.message,
            "actor": notification.actor.username if notification.actor else None,
            "recipient": notification.recipient.username,
            "todo_id": notification.todo_id,
            "todo_title": notification.todo.title,
            "created_at": notification.created_at,
        } for notification in Notification.objects.select_related(
            "actor", "recipient", "todo"
        ).order_by("-created_at")[:10]]

        return Response({
            "overview": {
                "total_users": users.count(),
                "total_teams": Team.objects.count(),
                "total_todos": total_todos,
                "incomplete_todos": incomplete_todos,
                "completed_todos": completed_todos,
                "pending_assignments": pending_assignments,
                "completion_rate": round(
                    completed_todos / total_todos * 100
                ) if total_todos else 0,
            },
            "task_status": {
                "pending": todos.filter(task_status=Todo.TaskStatus.PENDING).count(),
                "in_progress": todos.filter(task_status=Todo.TaskStatus.IN_PROGRESS).count(),
                "completed": completed_todos,
            },
            "teams": team_activity,
            "users": user_activity,
            "attention": attention,
            "recent_activity": recent_activity,
        })


class AdminUserTodosView(APIView):
    """Read-only inspection of todos created by or assigned to a user."""

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request, pk):
        user = get_object_or_404(User.objects.select_related("profile__team"), pk=pk)
        todos = Todo.objects.filter(
            Q(user=user) | Q(assignee=user)
        ).select_related("user", "assignee", "team").order_by("-updated_at")

        results = [{
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "creator": todo.user.username,
            "assignee": todo.assignee.username if todo.assignee else None,
            "team": todo.team.name if todo.team else None,
            "task_status": todo.task_status,
            "assignment_status": todo.assignment_status,
            "created_at": todo.created_at,
            "updated_at": todo.updated_at,
        } for todo in todos]

        return Response({
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.profile.role,
                "team": user.profile.team.name if user.profile.team else None,
            },
            "results": results,
            "count": len(results),
        })


class AdminTodoExplorerView(APIView):
    """Search and filter workspace todos without granting mutation access."""

    permission_classes = [IsAuthenticated, IsAdminUserRole]

    def get(self, request):
        todos = Todo.objects.select_related(
            "user", "assignee", "team"
        ).all()

        search = request.query_params.get("search", "").strip()
        if search:
            todos = todos.filter(
                Q(title__icontains=search)
                | Q(description__icontains=search)
                | Q(user__username__icontains=search)
                | Q(assignee__username__icontains=search)
                | Q(team__name__icontains=search)
            )

        team_id = request.query_params.get("team")
        if team_id:
            if not team_id.isdigit():
                return Response({"detail": "team must be a numeric team ID."}, status=400)
            todos = todos.filter(team_id=int(team_id))

        task_status = request.query_params.get("status")
        valid_statuses = {value for value, _label in Todo.TaskStatus.choices}
        if task_status:
            normalized_status = task_status.upper()
            if normalized_status not in valid_statuses:
                return Response({"detail": "Invalid task status."}, status=400)
            todos = todos.filter(task_status=normalized_status)

        assignment_status = request.query_params.get("assignment_status")
        valid_assignment_statuses = {
            value for value, _label in Todo.AssignmentStatus.choices
        }
        if assignment_status:
            normalized_assignment_status = assignment_status.upper()
            if normalized_assignment_status not in valid_assignment_statuses:
                return Response({"detail": "Invalid assignment status."}, status=400)
            todos = todos.filter(assignment_status=normalized_assignment_status)

        unassigned = request.query_params.get("unassigned")
        if unassigned == "true":
            todos = todos.filter(assignee__isnull=True)
        elif unassigned not in (None, "", "false"):
            return Response({"detail": "unassigned must be true or false."}, status=400)

        creator_id = request.query_params.get("creator")
        assignee_id = request.query_params.get("assignee")
        for parameter, value in (("creator", creator_id), ("assignee", assignee_id)):
            if value and not value.isdigit():
                return Response({"detail": f"{parameter} must be a numeric user ID."}, status=400)
        if creator_id:
            todos = todos.filter(user_id=int(creator_id))
        if assignee_id:
            todos = todos.filter(assignee_id=int(assignee_id))

        ordering = request.query_params.get("ordering", "-updated_at")
        allowed_ordering = {"created_at", "-created_at", "updated_at", "-updated_at", "title", "-title"}
        if ordering not in allowed_ordering:
            return Response({"detail": "Invalid ordering."}, status=400)
        todos = todos.order_by(ordering, "-id")

        paginator = TodoPagination()
        page = paginator.paginate_queryset(todos, request)
        results = [{
            "id": todo.id,
            "title": todo.title,
            "description": todo.description,
            "creator": todo.user.username,
            "creator_id": todo.user_id,
            "assignee": todo.assignee.username if todo.assignee else None,
            "assignee_id": todo.assignee_id,
            "team": todo.team.name if todo.team else None,
            "team_id": todo.team_id,
            "task_status": todo.task_status,
            "assignment_status": todo.assignment_status,
            "created_at": todo.created_at,
            "updated_at": todo.updated_at,
        } for todo in page]

        return paginator.get_paginated_response(results)
