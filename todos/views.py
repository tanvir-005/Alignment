from django.contrib.auth import get_user_model
from django.db.models import Case, Count, IntegerField, Q, Value, When, Exists, OuterRef
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_serializers import EmailOrUsernameTokenSerializer, RegisterSerializer
from .models import (
    Notification,
    Team,
    TeamMembership,
    Todo,
    TodoActivity,
    TodoAssignment,
)
from .pagination import DefaultPagination, TodoPagination
from .permissions import IsAdminRole, can_view_team, is_admin, member_team_ids, pm_team_ids
from .selectors import (
    actionable_q,
    annotated_teams,
    assigned_to,
    teams_visible_to,
    todos_visible_to,
    unassigned_users,
)
from .serializers import (
    AddMembersSerializer,
    AdminUserSerializer,
    NotificationSerializer,
    ReplacePMSerializer,
    TeamDetailSerializer,
    TeamSerializer,
    TeamWriteSerializer,
    TodoActivitySerializer,
    TodoCreateSerializer,
    TodoSerializer,
    TodoStatusSerializer,
    TodoUpdateSerializer,
)
from .services import team_service, todo_service
from .utils.names import display_name

User = get_user_model()


# ======================================================================= auth
class LoginView(TokenObtainPairView):
    serializer_class = EmailOrUsernameTokenSerializer


class RegisterView(APIView):
    permission_classes = []
    authentication_classes = []

    @extend_schema(request=RegisterSerializer, responses={201: OpenApiTypes.OBJECT}, operation_id="register_user")
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {
                "message": "Account created. An administrator will add you to a team.",
                "user": {"id": user.id, "name": display_name(user), "email": user.email},
            },
            status=status.HTTP_201_CREATED,
        )


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        user = request.user
        admin = is_admin(user)
        memberships = (
            []
            if admin
            else user.team_memberships.select_related("team").order_by("team__name")
        )
        return Response(
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "name": display_name(user),
                "role": "ADMIN" if admin else "USER",
                "is_admin": admin,
                "memberships": [
                    {
                        "team": {"id": m.team_id, "name": m.team.name, "color": m.team.color},
                        "role": m.role,
                    }
                    for m in memberships
                ],
                "pm_team_ids": sorted(pm_team_ids(user)) if not admin else [],
                "has_team": admin or bool(memberships),
            }
        )


# ======================================================================= teams
def _team_response(request, team_id, *, status_code=200):
    team = get_object_or_404(annotated_teams(Team.objects.filter(pk=team_id)))
    open_tasks = dict(
        TodoAssignment.objects.filter(todo__team=team)
        .exclude(todo__status=Todo.Status.COMPLETED)
        .values_list("user_id")
        .annotate(n=Count("id"))
    )
    data = TeamDetailSerializer(
        team, context={"request": request, "open_tasks": open_tasks}
    ).data
    return Response(data, status=status_code)


class TeamListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=TeamSerializer(many=True))
    def get(self, request):
        teams = annotated_teams(teams_visible_to(request.user))
        return Response(TeamSerializer(teams, many=True, context={"request": request}).data)

    @extend_schema(request=TeamWriteSerializer, responses=TeamDetailSerializer)
    def post(self, request):
        if not is_admin(request.user):
            self.permission_denied(request, message="Only administrators can create teams.")
        serializer = TeamWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if "pm_id" not in data:
            raise ValidationError({"pm_id": "Every team needs a project manager."})
        pm = get_object_or_404(User, pk=data["pm_id"])
        team = team_service.create_team(
            actor=request.user,
            name=data["name"],
            description=data.get("description", ""),
            color=data.get("color"),
            pm=pm,
        )
        return _team_response(request, team.id, status_code=status.HTTP_201_CREATED)


class TeamDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _team(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        if not can_view_team(request.user, team.id):
            # Do not reveal teams a user does not belong to.
            from django.http import Http404
            raise Http404
        return team

    @extend_schema(responses=TeamDetailSerializer)
    def get(self, request, pk):
        team = self._team(request, pk)
        return _team_response(request, team.id)

    @extend_schema(request=TeamWriteSerializer, responses=TeamDetailSerializer)
    def patch(self, request, pk):
        if not is_admin(request.user):
            self.permission_denied(request, message="Only administrators can edit teams.")
        team = get_object_or_404(Team, pk=pk)
        serializer = TeamWriteSerializer(team, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        data.pop("pm_id", None)  # PM changes go through replace-pm
        team_service.update_team(team=team, **data)
        return _team_response(request, team.id)

    def delete(self, request, pk):
        if not is_admin(request.user):
            self.permission_denied(request, message="Only administrators can delete teams.")
        team = get_object_or_404(Team, pk=pk)
        team_service.delete_team(actor=request.user, team=team)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TeamMembersView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(request=AddMembersSerializer, responses=TeamDetailSerializer)
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        serializer = AddMembersSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = set(serializer.validated_data["user_ids"])
        users = list(User.objects.filter(id__in=ids))
        if len(users) != len(ids):
            raise ValidationError({"user_ids": "One or more users do not exist."})
        team_service.add_members(actor=request.user, team=team, users=users)
        return _team_response(request, team.id)


class TeamMemberDetailView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        responses=inline_serializer(
            "RemoveMemberResult",
            {
                "assigned": serializers.IntegerField(),
                "deleted_todos": serializers.IntegerField(),
            },
        )
    )
    def delete(self, request, pk, user_id):
        team = get_object_or_404(Team, pk=pk)
        user = get_object_or_404(User, pk=user_id)
        result = team_service.remove_member(actor=request.user, team=team, user=user)
        return Response(result)


class TeamMemberImpactView(APIView):
    """What removing this member would do - shown in the confirmation dialog."""

    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        responses=inline_serializer(
            "MemberImpact",
            {
                "is_pm": serializers.BooleanField(),
                "assigned": serializers.IntegerField(),
                "to_delete": serializers.IntegerField(),
            },
        )
    )
    def get(self, request, pk, user_id):
        team = get_object_or_404(Team, pk=pk)
        membership = get_object_or_404(TeamMembership, team=team, user_id=user_id)
        impact = team_service.removal_impact(team=team, user=membership.user)
        return Response(
            {
                "is_pm": membership.role == TeamMembership.Role.PM,
                "assigned": impact["assigned"],
                "to_delete": impact["to_delete"],
            }
        )


class TeamReplacePMView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(request=ReplacePMSerializer, responses=TeamDetailSerializer)
    def post(self, request, pk):
        team = get_object_or_404(Team, pk=pk)
        serializer = ReplacePMSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_pm = get_object_or_404(User, pk=serializer.validated_data["pm_id"])
        team_service.replace_pm(
            actor=request.user,
            team=team,
            new_pm=new_pm,
            old_pm_action=serializer.validated_data["old_pm_action"],
        )
        return _team_response(request, team.id)


# ======================================================================= users (admin)
class UserListView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(
        parameters=[
            OpenApiParameter("search", str),
            OpenApiParameter("unassigned", bool),
            OpenApiParameter("active", bool),
            OpenApiParameter("exclude_team", int),
        ],
        responses=AdminUserSerializer(many=True),
    )
    def get(self, request):
        p = request.query_params
        qs = (
            User.objects.exclude(profile__role="ADMIN")
            .exclude(is_superuser=True)
            .prefetch_related("team_memberships__team")
            .order_by("first_name", "last_name", "username")
        )
        if p.get("active") in ("true", "false"):
            qs = qs.filter(is_active=(p["active"] == "true"))
        if p.get("unassigned") == "true":
            qs = qs.filter(is_active=True, team_memberships__isnull=True)
        if p.get("exclude_team", "").isdigit():
            qs = qs.exclude(team_memberships__team_id=int(p["exclude_team"]))
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
                | Q(username__icontains=search)
            )
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(AdminUserSerializer(page, many=True).data)


class UserActivationView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    activate = False

    @extend_schema(request=None, responses=AdminUserSerializer)
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if self.activate:
            user.is_active = True
            user.save(update_fields=["is_active"])
        else:
            team_service.deactivate_user(actor=request.user, user=user)
        user = User.objects.prefetch_related("team_memberships__team").get(pk=pk)
        return Response(AdminUserSerializer(user).data)


# ======================================================================= todos
PRIORITY_ORDER = Case(
    When(priority=Todo.Priority.HIGH, then=Value(0)),
    When(priority=Todo.Priority.MEDIUM, then=Value(1)),
    default=Value(2),
    output_field=IntegerField(),
)

ORDERINGS = {
    "newest": ("-created_at", "-id"),
    "oldest": ("created_at", "id"),
    "updated": ("-updated_at", "-id"),
    "due": ("due_date_null", "due_date", "-id"),
    "priority": ("priority_rank", "-id"),
}


def _todo_ctx(request):
    return {"request": request}


class TodoListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter("scope", str, enum=["all", "actionable", "mine", "other"]),
            OpenApiParameter("team", int),
            OpenApiParameter("status", str),
            OpenApiParameter("priority", str),
            OpenApiParameter("assignee", int),
            OpenApiParameter("search", str),
            OpenApiParameter("ordering", str, enum=list(ORDERINGS)),
        ],
        responses=TodoSerializer(many=True),
    )
    def get(self, request):
        user, p = request.user, request.query_params
        qs = todos_visible_to(user)

        scope = p.get("scope", "all")
        if scope == "actionable":
            qs = qs.none() if is_admin(user) else qs.filter(actionable_q(user))
        elif scope == "mine":
            qs = qs.none() if is_admin(user) else qs.filter(assigned_to(user))
        elif scope == "other":
            qs = qs if is_admin(user) else qs.exclude(actionable_q(user))

        if p.get("team", "").isdigit():
            qs = qs.filter(team_id=int(p["team"]))
        if p.get("status") in Todo.Status.values:
            qs = qs.filter(status=p["status"])
        if p.get("priority") in Todo.Priority.values:
            qs = qs.filter(priority=p["priority"])
        if p.get("assignee", "").isdigit():
            qs = qs.filter(
                Exists(
                    TodoAssignment.objects.filter(
                        todo=OuterRef("pk"), user_id=int(p["assignee"])
                    )
                )
            )
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

        ordering = p.get("ordering", "newest")
        if ordering not in ORDERINGS:
            ordering = "newest"
        qs = qs.annotate(
            priority_rank=PRIORITY_ORDER,
            due_date_null=Case(
                When(due_date__isnull=True, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
        ).order_by(*ORDERINGS[ordering])

        paginator = TodoPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        data = TodoSerializer(page, many=True, context=_todo_ctx(request)).data
        return paginator.get_paginated_response(data)

    @extend_schema(request=TodoCreateSerializer, responses=TodoSerializer)
    def post(self, request):
        if is_admin(request.user):
            self.permission_denied(
                request, message="Administrators cannot create tasks. Ask a project manager."
            )
        serializer = TodoCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        team = get_object_or_404(Team, pk=data.pop("team_id"))
        todo = todo_service.create_todo(actor=request.user, team=team, **data)
        todo = todos_visible_to(request.user).get(pk=todo.pk)
        return Response(
            TodoSerializer(todo, context=_todo_ctx(request)).data,
            status=status.HTTP_201_CREATED,
        )


class TodoDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _todo(self, request, pk):
        return get_object_or_404(todos_visible_to(request.user), pk=pk)

    @extend_schema(responses=TodoSerializer)
    def get(self, request, pk):
        todo = self._todo(request, pk)
        return Response(TodoSerializer(todo, context=_todo_ctx(request)).data)

    @extend_schema(request=TodoUpdateSerializer, responses=TodoSerializer)
    def patch(self, request, pk):
        todo = self._todo(request, pk)
        serializer = TodoUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        todo_service.update_todo(
            actor=request.user, todo=todo, **serializer.validated_data
        )
        todo = self._todo(request, pk)
        return Response(TodoSerializer(todo, context=_todo_ctx(request)).data)

    def delete(self, request, pk):
        todo = self._todo(request, pk)
        todo_service.delete_todo(actor=request.user, todo=todo)
        return Response(status=status.HTTP_204_NO_CONTENT)


class TodoStatusView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=TodoStatusSerializer, responses=TodoSerializer)
    def patch(self, request, pk):
        todo = get_object_or_404(todos_visible_to(request.user), pk=pk)
        serializer = TodoStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        todo_service.change_status(
            actor=request.user, todo=todo, status=serializer.validated_data["status"]
        )
        todo = get_object_or_404(todos_visible_to(request.user), pk=pk)
        return Response(TodoSerializer(todo, context=_todo_ctx(request)).data)


class TodoActivityListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=TodoActivitySerializer(many=True))
    def get(self, request, pk):
        todo = get_object_or_404(todos_visible_to(request.user), pk=pk)
        activities = todo.activities.select_related("actor")
        return Response(TodoActivitySerializer(activities, many=True).data)


# ======================================================================= notifications
class NotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter("unread", bool)],
        responses=NotificationSerializer(many=True),
    )
    def get(self, request):
        qs = Notification.objects.filter(recipient=request.user).select_related("actor")
        if request.query_params.get("unread") == "true":
            qs = qs.filter(is_read=False)
        paginator = DefaultPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(
            NotificationSerializer(page, many=True).data
        )


class NotificationUnreadCountView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses=inline_serializer(
            "UnreadCount", {"unread_count": serializers.IntegerField()}
        )
    )
    def get(self, request):
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({"unread_count": count})


class NotificationMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=None, responses=NotificationSerializer)
    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses=inline_serializer("MarkAllRead", {"updated": serializers.IntegerField()}),
    )
    def patch(self, request):
        updated = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).update(is_read=True)
        return Response({"updated": updated})


# ======================================================================= admin overview
class AdminOverviewView(APIView):
    permission_classes = [IsAuthenticated, IsAdminRole]

    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        today = timezone.localdate()
        status_counts = {s: 0 for s in Todo.Status.values}
        for row in Todo.objects.values("status").annotate(n=Count("id")):
            status_counts[row["status"]] = row["n"]

        people = User.objects.filter(is_active=True).exclude(profile__role="ADMIN").exclude(
            is_superuser=True
        )
        teams = annotated_teams()

        workload_rows = list(
            TodoAssignment.objects.exclude(todo__status=Todo.Status.COMPLETED)
            .values("user_id")
            .annotate(n=Count("id"))
            .order_by("-n")[:6]
        )
        users = {u.id: u for u in User.objects.filter(id__in=[r["user_id"] for r in workload_rows])}

        recent = TodoActivity.objects.select_related("actor", "todo", "todo__team")[:10]

        return Response(
            {
                "totals": {
                    "teams": Team.objects.count(),
                    "active_users": people.count(),
                    "unassigned_users": unassigned_users().count(),
                    "todos": sum(status_counts.values()),
                    "open_todos": status_counts["PENDING"] + status_counts["IN_PROGRESS"],
                    "overdue": Todo.objects.filter(due_date__lt=today)
                    .exclude(status=Todo.Status.COMPLETED)
                    .count(),
                },
                "status_counts": status_counts,
                "teams": TeamSerializer(teams, many=True, context={"request": request}).data,
                "workload": [
                    {
                        "user": {
                            "id": r["user_id"],
                            "name": display_name(users[r["user_id"]]),
                        },
                        "open_tasks": r["n"],
                    }
                    for r in workload_rows
                    if r["user_id"] in users
                ],
                "recent_activity": [
                    {
                        "id": a.id,
                        "description": a.description,
                        "created_at": a.created_at,
                        "todo_id": a.todo_id,
                        "todo_title": a.todo.title,
                        "team": {
                            "id": a.todo.team_id,
                            "name": a.todo.team.name,
                            "color": a.todo.team.color,
                        },
                    }
                    for a in recent
                ],
            }
        )
