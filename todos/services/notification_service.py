from todos.models import Notification


def notify(*, recipients, actor=None, message, todo=None, team=None):
    """Create one notification per distinct recipient (never for the actor)."""
    seen = set()
    rows = []
    for recipient in recipients:
        if recipient is None or recipient.id in seen:
            continue
        if actor is not None and recipient.id == actor.id:
            continue
        seen.add(recipient.id)
        rows.append(
            Notification(
                recipient=recipient,
                actor=actor,
                todo=todo,
                team=team,
                message=message[:255],
            )
        )
    if rows:
        Notification.objects.bulk_create(rows)
    return rows
