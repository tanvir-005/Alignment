"""
Team & membership business rules. Only administrators reach these functions
(enforced by the views). All mutations are atomic.

Invariants kept here:
  * every team has exactly one PM, set when the team is created;
  * the PM can only be changed through replace_pm() (atomic swap);
  * a PM cannot be removed from a team directly;
  * removing a member deletes their assignments in that team, and deletes every
    todo that member was the LAST assignee of.
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count
from rest_framework.exceptions import ValidationError

from todos.models import (
    TEAM_COLORS,
    Team,
    TeamMembership,
    Todo,
    TodoAssignment,
    TodoDeletion,
)
from todos.permissions import is_admin
from todos.utils.names import display_name

from .notification_service import notify

User = get_user_model()


def _ensure_assignable(user):
    if not user.is_active:
        raise ValidationError(f"{display_name(user)} is deactivated.")
    if is_admin(user):
        raise ValidationError("Administrators cannot be team members.")


@transaction.atomic
def create_team(*, actor, name, pm, description="", color=None):
    _ensure_assignable(pm)
    if color is None:
        color = TEAM_COLORS[Team.objects.count() % len(TEAM_COLORS)]
    team = Team.objects.create(name=name, description=description, color=color)
    TeamMembership.objects.create(team=team, user=pm, role=TeamMembership.Role.PM)
    notify(
        recipients=[pm],
        actor=actor,
        team=team,
        message=f"You are now the project manager of {team.name}.",
    )
    return team


@transaction.atomic
def update_team(*, team, **fields):
    for key in ("name", "description", "color"):
        if key in fields:
            setattr(team, key, fields[key])
    team.save()
    return team


@transaction.atomic
def delete_team(*, actor, team):
    members = [m.user for m in team.memberships.select_related("user")]
    name = team.name
    team.delete()  # cascades memberships, todos, assignments, activities
    notify(
        recipients=members,
        actor=actor,
        message=f'The team "{name}" was deleted.',
    )


@transaction.atomic
def add_members(*, actor, team, users):
    added = []
    existing = set(team.memberships.values_list("user_id", flat=True))
    for user in users:
        _ensure_assignable(user)
        if user.id in existing:
            continue
        TeamMembership.objects.create(
            team=team, user=user, role=TeamMembership.Role.MEMBER
        )
        existing.add(user.id)
        added.append(user)
    notify(
        recipients=added,
        actor=actor,
        team=team,
        message=f"You were added to the team {team.name}.",
    )
    return added


def removal_impact(*, team, user):
    """What removing `user` from `team` would do. Used for the confirm dialog."""
    todo_ids = list(
        TodoAssignment.objects.filter(todo__team=team, user=user).values_list(
            "todo_id", flat=True
        )
    )
    counts = (
        TodoAssignment.objects.filter(todo_id__in=todo_ids)
        .values("todo_id")
        .annotate(n=Count("id"))
    )
    sole = [c["todo_id"] for c in counts if c["n"] == 1]
    return {"assigned": len(todo_ids), "to_delete": len(sole), "to_delete_ids": sole}


@transaction.atomic
def remove_member(*, actor, team, user):
    membership = (
        TeamMembership.objects.select_for_update()
        .filter(team=team, user=user)
        .first()
    )
    if membership is None:
        raise ValidationError("This user is not a member of the team.")
    if membership.role == TeamMembership.Role.PM:
        raise ValidationError(
            "A team cannot be left without a project manager. "
            "Replace the project manager first."
        )

    impact = removal_impact(team=team, user=user)
    TodoAssignment.objects.filter(todo__team=team, user=user).delete()
    doomed = list(Todo.objects.filter(id__in=impact["to_delete_ids"]))
    TodoDeletion.objects.bulk_create(
        [
            TodoDeletion(
                team=team,
                title=t.title,
                actor=actor,
                reason=f"{display_name(user)} was removed from the team and was its only assignee",
            )
            for t in doomed
        ]
    )
    Todo.objects.filter(id__in=impact["to_delete_ids"]).delete()
    membership.delete()

    pm = team.memberships.filter(role=TeamMembership.Role.PM).select_related("user").first()
    name = display_name(user)
    summary = f"{name} was removed from {team.name}."
    if impact["to_delete"]:
        summary += f" {impact['to_delete']} task(s) they were the only assignee of were deleted."
    notify(recipients=[pm.user if pm else None], actor=actor, team=team, message=summary)
    notify(
        recipients=[user],
        actor=actor,
        message=f"You were removed from the team {team.name}.",
    )
    return {"assigned": impact["assigned"], "deleted_todos": impact["to_delete"]}


@transaction.atomic
def replace_pm(*, actor, team, new_pm, old_pm_action="member"):
    if old_pm_action not in ("member", "remove"):
        raise ValidationError("old_pm_action must be 'member' or 'remove'.")

    current = TeamMembership.objects.select_for_update().get(
        team=team, role=TeamMembership.Role.PM
    )
    if current.user_id == new_pm.id:
        raise ValidationError("This user is already the project manager.")
    _ensure_assignable(new_pm)

    old_user = current.user
    # Demote first so the one-PM-per-team constraint is never violated.
    current.role = TeamMembership.Role.MEMBER
    current.save(update_fields=["role"])

    membership, created = TeamMembership.objects.get_or_create(
        team=team, user=new_pm, defaults={"role": TeamMembership.Role.PM}
    )
    if not created:
        membership.role = TeamMembership.Role.PM
        membership.save(update_fields=["role"])

    if old_pm_action == "remove":
        remove_member(actor=actor, team=team, user=old_user)

    notify(
        recipients=[new_pm],
        actor=actor,
        team=team,
        message=f"You are now the project manager of {team.name}.",
    )
    if old_pm_action == "member":
        notify(
            recipients=[old_user],
            actor=actor,
            team=team,
            message=f"You are no longer the project manager of {team.name}.",
        )
    return team


@transaction.atomic
def deactivate_user(*, actor, user):
    if user.id == actor.id:
        raise ValidationError("You cannot deactivate yourself.")
    if is_admin(user):
        raise ValidationError("Administrator accounts cannot be deactivated here.")
    pm_of = list(
        Team.objects.filter(
            memberships__user=user, memberships__role=TeamMembership.Role.PM
        ).values_list("name", flat=True)
    )
    if pm_of:
        raise ValidationError(
            "Replace this user as project manager first: " + ", ".join(pm_of) + "."
        )
    for membership in list(user.team_memberships.select_related("team")):
        remove_member(actor=actor, team=membership.team, user=user)
    user.is_active = False
    user.save(update_fields=["is_active"])
    return user
