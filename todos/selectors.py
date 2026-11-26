from django.contrib.auth import get_user_model
from django.db.models import Count, Exists, OuterRef, Prefetch, Q

from .models import Team, TeamMembership, Todo, TodoAssignment
from .permissions import is_admin, member_team_ids, pm_team_ids

User = get_user_model()


def assigned_to(user):
    return Exists(TodoAssignment.objects.filter(todo=OuterRef("pk"), user=user))


def base_todos():
    return Todo.objects.select_related("team", "created_by").prefetch_related(
        Prefetch("assignments", queryset=TodoAssignment.objects.select_related("user"))
    )


def todos_visible_to(user):
    """Admin: everything. Everyone else: todos of the teams they belong to."""
    qs = base_todos()
    if is_admin(user):
        return qs
    return qs.filter(team_id__in=member_team_ids(user))


def actionable_q(user):
    """Todos whose status this user can change (assigned, or PM of the team)."""
    return Q(assigned_to(user)) | Q(team_id__in=pm_team_ids(user))


def teams_visible_to(user):
    qs = Team.objects.all()
    if not is_admin(user):
        qs = qs.filter(id__in=member_team_ids(user))
    return qs


def annotated_teams(qs=None):
    qs = Team.objects.all() if qs is None else qs
    return (
        qs.annotate(
            member_count=Count("memberships", distinct=True),
            n_pending=Count("todos", filter=Q(todos__status=Todo.Status.PENDING), distinct=True),
            n_in_progress=Count(
                "todos", filter=Q(todos__status=Todo.Status.IN_PROGRESS), distinct=True
            ),
            n_completed=Count(
                "todos", filter=Q(todos__status=Todo.Status.COMPLETED), distinct=True
            ),
        )
        .prefetch_related(
            Prefetch(
                "memberships",
                queryset=TeamMembership.objects.select_related("user"),
            )
        )
        .order_by("name")
    )


def unassigned_users():
    """Active, non-admin users who belong to no team yet."""
    return (
        User.objects.filter(is_active=True, team_memberships__isnull=True)
        .exclude(profile__role="ADMIN")
        .exclude(is_superuser=True)
    )
