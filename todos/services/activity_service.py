from todos.models import TodoActivity


def record_todo_activity(*, todo, actor, event_type, description, metadata=None):
    """Call inside the same transaction as the change that caused it."""
    return TodoActivity.objects.create(
        todo=todo,
        actor=actor,
        event_type=event_type,
        description=description[:255],
        metadata=metadata or {},
    )
