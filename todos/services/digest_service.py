"""Daily per-team digest for project managers, built from the activity log."""
from collections import OrderedDict
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone

from todos.models import DigestLog, Todo, TodoActivity, TodoDeletion
from todos.utils.names import display_name

from . import email_service

MAX_TASKS_SHOWN = 40


def _stamp(dt):
    return timezone.localtime(dt).strftime("%d %b %H:%M")


def build_digest(*, team, since, until):
    """Return the template context for one team, or None if nothing changed."""
    activities = list(
        TodoActivity.objects.filter(
            todo__team=team, created_at__gte=since, created_at__lt=until
        )
        .select_related("todo")
        .order_by("created_at", "id")
    )
    deletions = list(
        TodoDeletion.objects.filter(team=team, created_at__gte=since, created_at__lt=until)
        .select_related("actor")
        .order_by("created_at", "id")
    )
    if not activities and not deletions:
        return None

    kinds = [a.event_type for a in activities]
    completed = sum(
        1
        for a in activities
        if a.event_type == TodoActivity.EventType.STATUS_CHANGED
        and a.metadata.get("to") == Todo.Status.COMPLETED
    )
    counts = [
        ("Created", kinds.count(TodoActivity.EventType.CREATED)),
        ("Status changes", kinds.count(TodoActivity.EventType.STATUS_CHANGED)),
        ("Completed", completed),
        ("Reassigned", kinds.count(TodoActivity.EventType.ASSIGNEES_CHANGED)),
        ("Deleted", len(deletions)),
    ]

    grouped = OrderedDict()
    for a in activities:
        entry = grouped.setdefault(
            a.todo_id,
            {"title": a.todo.title, "url": email_service.task_url(a.todo_id), "events": []},
        )
        entry["events"].append({"time": _stamp(a.created_at), "text": a.description})
    tasks = list(grouped.values())

    status_rows = dict(
        Todo.objects.filter(team=team).values_list("status").annotate(n=Count("id"))
    )
    overdue = (
        Todo.objects.filter(team=team, due_date__lt=timezone.localdate())
        .exclude(status=Todo.Status.COMPLETED)
        .count()
    )

    def deletion_text(d):
        text = f"“{d.title}” was deleted"
        if d.reason:
            text += f" ({d.reason})"
        elif d.actor:
            text += f" by {display_name(d.actor)}"
        return text + "."

    return {
        **email_service._team_context(team),
        "hours": round((until - since).total_seconds() / 3600),
        "window": f"{_stamp(since)} – {_stamp(until)}",
        "counts": counts,
        "tasks": tasks[:MAX_TASKS_SHOWN],
        "more_tasks": max(0, len(tasks) - MAX_TASKS_SHOWN),
        "deleted": [{"time": _stamp(d.created_at), "text": deletion_text(d)} for d in deletions],
        "now_pending": status_rows.get(Todo.Status.PENDING, 0),
        "now_progress": status_rows.get(Todo.Status.IN_PROGRESS, 0),
        "now_done": status_rows.get(Todo.Status.COMPLETED, 0),
        "overdue": overdue,
        "url": email_service.team_url(team.id),
        "event_count": len(activities) + len(deletions),
    }


def send_digest(*, team, pm, context, until):
    """Send one digest and record it. Returns True if the email went out."""
    ctx = {**context, "recipient_name": display_name(pm)}
    ok = email_service.deliver(
        subject=f"[{team.name}] Daily summary — {timezone.localtime(until).strftime('%d %b %Y')}",
        to=pm.email,
        template="daily_digest",
        context=ctx,
    )
    if ok:
        DigestLog.objects.update_or_create(
            team=team,
            date=timezone.localdate(until),
            defaults={"recipient": pm, "event_count": context["event_count"]},
        )
    return ok


def default_window(hours=24, now=None):
    until = now or timezone.now()
    return until - timedelta(hours=hours), until
