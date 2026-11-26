"""
Single source of truth for who may do what.

  * Admin       - owner/spectator. Manages teams & membership. Never creates or
                  changes todos. Sees everything (read-only).
  * PM          - per-team role. Creates/edits/deletes/assigns todos of that
                  team and may change their status.
  * Assignee    - may change the status of a todo assigned to them.
  * Member      - may view all todos of the teams they belong to.
"""
from rest_framework.permissions import BasePermission

from .models import TeamMembership, UserProfile


def is_admin(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    cached = getattr(user, "_is_admin", None)
    if cached is None:
        profile = getattr(user, "profile", None)
        cached = bool(user.is_superuser or (profile and profile.role == UserProfile.Role.ADMIN))
        user._is_admin = cached
    return cached


def membership_map(user) -> dict:
    """{team_id: role} for the user. Cached on the user instance (per request)."""
    cached = getattr(user, "_membership_map", None)
    if cached is None:
        cached = dict(
            TeamMembership.objects.filter(user=user).values_list("team_id", "role")
        )
        user._membership_map = cached
    return cached


def member_team_ids(user) -> set:
    return set(membership_map(user).keys())


def pm_team_ids(user) -> set:
    return {t for t, r in membership_map(user).items() if r == TeamMembership.Role.PM}


def is_team_member(user, team_id) -> bool:
    return team_id in membership_map(user)


def is_team_pm(user, team_id) -> bool:
    return membership_map(user).get(team_id) == TeamMembership.Role.PM


def can_view_team(user, team_id) -> bool:
    return is_admin(user) or is_team_member(user, team_id)


def can_view_todo(user, todo) -> bool:
    return can_view_team(user, todo.team_id)


def is_assignee(user, todo) -> bool:
    # Uses prefetched assignments when available.
    return any(a.user_id == user.id for a in todo.assignments.all())


def can_edit_todo(user, todo) -> bool:
    """Title/description/priority/due date/assignees/delete: PM of the team only."""
    return not is_admin(user) and is_team_pm(user, todo.team_id)


def can_change_status(user, todo) -> bool:
    """Any assignee, or the team's PM. Never the admin."""
    if is_admin(user):
        return False
    return is_team_pm(user, todo.team_id) or is_assignee(user, todo)


class IsAdminRole(BasePermission):
    message = "Only administrators can do this."

    def has_permission(self, request, view):
        return is_admin(request.user)
