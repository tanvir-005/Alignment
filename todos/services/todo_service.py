"""
Todo business rules.

  * create / edit / assign / delete  -> PM of the todo's team only
  * change status                    -> any assignee, or the team's PM
  * every todo has at least one assignee, and every assignee is a current
    (active) member of the todo's team
"""
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from todos.models import Todo, TodoActivity, TodoAssignment, TodoDeletion
from todos.permissions import can_change_status, can_edit_todo, is_team_pm
from todos.utils.names import display_name

from .activity_service import record_todo_activity
from . import email_service
from .notification_service import notify

User = get_user_model()

EDITABLE_FIELDS = ("title", "description", "priority", "due_date")


def resolve_assignees(*, team, assignee_ids=None, all_members=False):
    members = User.objects.filter(
        team_memberships__team=team, is_active=True
    ).distinct()
    if all_members:
        users = list(members)
    else:
        ids = set(assignee_ids or [])
        users = list(members.filter(id__in=ids))
        if len(users) != len(ids):
            raise ValidationError("All assignees must be active members of this team.")
    if not users:
        raise ValidationError("A task needs at least one assignee.")
    return users


@transaction.atomic
def create_todo(*, actor, team, title, assignee_ids=None, all_members=False, **fields):
    if not is_team_pm(actor, team.id):
        raise PermissionDenied("Only the project manager of a team can create its tasks.")
    users = resolve_assignees(team=team, assignee_ids=assignee_ids, all_members=all_members)

    todo = Todo.objects.create(
        team=team,
        created_by=actor,
        title=title,
        description=fields.get("description", ""),
        priority=fields.get("priority", Todo.Priority.MEDIUM),
        due_date=fields.get("due_date"),
    )
    TodoAssignment.objects.bulk_create(
        [TodoAssignment(todo=todo, user=u, assigned_by=actor) for u in users]
    )
    names = ", ".join(display_name(u) for u in users)
    record_todo_activity(
        todo=todo,
        actor=actor,
        event_type=TodoActivity.EventType.CREATED,
        description=f"{display_name(actor)} created this task and assigned {names}.",
        metadata={"assignee_ids": [u.id for u in users]},
    )
    notify(
        recipients=users,
        actor=actor,
        todo=todo,
        team=team,
        message=f'{display_name(actor)} assigned you "{todo.title}" in {team.name}.',
    )
    email_service.task_assigned(todo=todo, recipients=users, actor=actor)
    return todo


@transaction.atomic
def update_todo(*, actor, todo, assignee_ids=None, all_members=False, **fields):
    if not can_edit_todo(actor, todo):
        raise PermissionDenied("Only the project manager of this team can edit the task.")

    changed = []
    for key in EDITABLE_FIELDS:
        if key in fields and getattr(todo, key) != fields[key]:
            setattr(todo, key, fields[key])
            changed.append(key.replace("_", " "))
    if changed:
        todo.save()
        record_todo_activity(
            todo=todo,
            actor=actor,
            event_type=TodoActivity.EventType.UPDATED,
            description=f"{display_name(actor)} updated {', '.join(changed)}.",
            metadata={"fields": changed},
        )

    if assignee_ids is not None or all_members:
        _set_assignees(actor=actor, todo=todo, assignee_ids=assignee_ids, all_members=all_members)

    todo.save()  # bump updated_at
    return todo


def _set_assignees(*, actor, todo, assignee_ids, all_members):
    new_users = resolve_assignees(
        team=todo.team, assignee_ids=assignee_ids, all_members=all_members
    )
    new_ids = {u.id for u in new_users}
    current = {a.user_id: a.user for a in todo.assignments.select_related("user")}
    added = [u for u in new_users if u.id not in current]
    removed = [u for uid, u in current.items() if uid not in new_ids]
    if not added and not removed:
        return

    if removed:
        TodoAssignment.objects.filter(todo=todo, user__in=removed).delete()
    TodoAssignment.objects.bulk_create(
        [TodoAssignment(todo=todo, user=u, assigned_by=actor) for u in added]
    )

    parts = []
    if added:
        parts.append("assigned " + ", ".join(display_name(u) for u in added))
    if removed:
        parts.append("unassigned " + ", ".join(display_name(u) for u in removed))
    record_todo_activity(
        todo=todo,
        actor=actor,
        event_type=TodoActivity.EventType.ASSIGNEES_CHANGED,
        description=f"{display_name(actor)} " + " and ".join(parts) + ".",
        metadata={"added": [u.id for u in added], "removed": [u.id for u in removed]},
    )
    notify(
        recipients=added,
        actor=actor,
        todo=todo,
        team=todo.team,
        message=f'{display_name(actor)} assigned you "{todo.title}" in {todo.team.name}.',
    )
    email_service.task_assigned(todo=todo, recipients=added, actor=actor)
    notify(
        recipients=removed,
        actor=actor,
        todo=todo,
        team=todo.team,
        message=f'You were unassigned from "{todo.title}" in {todo.team.name}.',
    )


@transaction.atomic
def change_status(*, actor, todo, status):
    if not can_change_status(actor, todo):
        raise PermissionDenied(
            "Only an assignee or the project manager can change this task's status."
        )
    if status not in Todo.Status.values:
        raise ValidationError("Invalid status.")
    if todo.status == status:
        return todo

    old_status = todo.status
    old_label = Todo.Status(todo.status).label
    todo.status = status
    todo.completed_at = timezone.now() if status == Todo.Status.COMPLETED else None
    todo.save()

    record_todo_activity(
        todo=todo,
        actor=actor,
        event_type=TodoActivity.EventType.STATUS_CHANGED,
        description=(
            f"{display_name(actor)} moved this from {old_label} "
            f"to {Todo.Status(status).label}."
        ),
        metadata={"from": old_label, "to": status},
    )

    recipients = [a.user for a in todo.assignments.select_related("user")]
    pm_membership = todo.team.memberships.filter(role="PM").select_related("user").first()
    if pm_membership:
        recipients.append(pm_membership.user)
    notify(
        recipients=recipients,
        actor=actor,
        todo=todo,
        team=todo.team,
        message=(
            f'{display_name(actor)} moved "{todo.title}" to '
            f"{Todo.Status(status).label}."
        ),
    )
    email_service.status_changed(todo=todo, actor=actor, old_status=old_status)
    return todo


@transaction.atomic
def delete_todo(*, actor, todo):
    if not can_edit_todo(actor, todo):
        raise PermissionDenied("Only the project manager of this team can delete the task.")
    recipients = [a.user for a in todo.assignments.select_related("user")]
    title, team = todo.title, todo.team
    TodoDeletion.objects.create(team=team, title=title, actor=actor)
    todo.delete()
    notify(
        recipients=recipients,
        actor=actor,
        team=team,
        message=f'"{title}" in {team.name} was deleted.',
    )
