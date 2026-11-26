"""
Transactional emails (assignment, status change) and the shared sender used by
the daily digest.

Rules
  * Emails are sent only after the database transaction commits, so a change
    that rolls back never produces an email.
  * A mail failure is logged and swallowed: it must never break an API request.
  * People are never emailed about their own actions.
  * The backend is whatever EMAIL_BACKEND says: console (demo) by default,
    SMTP in production.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template import Context
from django.template.loader import get_template, render_to_string
from django.utils import timezone

from todos.models import Todo, TeamMembership
from todos.utils.names import display_name

logger = logging.getLogger(__name__)

TEAM_HEX = {
    "blue": "#3946d6", "teal": "#0b8f9e", "green": "#2b9a4b", "amber": "#c98200",
    "orange": "#e0561b", "rose": "#d12f66", "violet": "#7b3fe4", "slate": "#566180",
}
STATUS_HEX = {"PENDING": "#c98200", "IN_PROGRESS": "#3946d6", "COMPLETED": "#0f9d73"}


def task_url(todo_id):
    return f"{settings.FRONTEND_URL}/todos/{todo_id}"


def team_url(team_id):
    return f"{settings.FRONTEND_URL}/teams/{team_id}"


def deliver(*, subject, to, template, context) -> bool:
    """Render and send one email synchronously. Returns True on success."""
    try:
        text = get_template(f"email/{template}.txt").template.render(
            Context(context, autoescape=False)
        )
        html = render_to_string(f"email/{template}.html", context)
        message = EmailMultiAlternatives(
            subject=subject, body=text, from_email=settings.DEFAULT_FROM_EMAIL, to=[to]
        )
        message.attach_alternative(html, "text/html")
        message.send()
        return True
    except Exception:
        logger.exception("Failed to send %s email to %s", template, to)
        return False


def _after_commit(**kwargs):
    transaction.on_commit(lambda: deliver(**kwargs))


def _team_context(team):
    return {"team_name": team.name, "team_color": TEAM_HEX.get(team.color, "#3946d6")}


def _pm_user(team):
    membership = (
        TeamMembership.objects.filter(team=team, role=TeamMembership.Role.PM)
        .select_related("user")
        .first()
    )
    return membership.user if membership else None


# --------------------------------------------------------------- assignment
def task_assigned(*, todo, recipients, actor):
    """Tell each newly assigned person about the task (not the actor)."""
    pm = _pm_user(todo.team)
    assignees = ", ".join(
        sorted(display_name(a.user) for a in todo.assignments.select_related("user"))
    )
    base = {
        **_team_context(todo.team),
        "actor_name": display_name(actor),
        "title": todo.title,
        "description": todo.description,
        "priority": Todo.Priority(todo.priority).label,
        "due_date": todo.due_date.strftime("%d %b %Y") if todo.due_date else "No due date",
        "assignees": assignees,
        "pm_name": display_name(pm) if pm else "—",
        "url": task_url(todo.id),
    }
    sent_to = set()
    for user in recipients:
        if not user.email or not user.is_active or user.id in sent_to:
            continue
        if actor is not None and user.id == actor.id:
            continue
        sent_to.add(user.id)
        _after_commit(
            subject=f"[{todo.team.name}] New task assigned: {todo.title}",
            to=user.email,
            template="task_assigned",
            context={**base, "recipient_name": display_name(user)},
        )


# ------------------------------------------------------------ status change
def status_changed(*, todo, actor, old_status):
    """Tell the team's PM that someone else changed a task's status."""
    pm = _pm_user(todo.team)
    if pm is None or not pm.email or not pm.is_active:
        return
    if actor is not None and pm.id == actor.id:
        return

    old_label = Todo.Status(old_status).label
    new_label = Todo.Status(todo.status).label
    assignees = ", ".join(
        sorted(display_name(a.user) for a in todo.assignments.select_related("user"))
    )
    _after_commit(
        subject=f'[{todo.team.name}] "{todo.title}" moved to {new_label}',
        to=pm.email,
        template="status_changed",
        context={
            **_team_context(todo.team),
            "recipient_name": display_name(pm),
            "actor_name": display_name(actor),
            "title": todo.title,
            "old_status": old_label,
            "new_status": new_label,
            "status_color": STATUS_HEX.get(todo.status, "#3946d6"),
            "assignees": assignees,
            "when": timezone.localtime().strftime("%d %b %Y, %H:%M"),
            "url": task_url(todo.id),
        },
    )
