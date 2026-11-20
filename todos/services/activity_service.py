
from todos.models import TodoActivity


def record_todo_activity(
    *,
    todo,
    actor,
    event_type,
    description,
    metadata=None,
):
    """
    Record an activity associated with a todo.

    This function should be called from the same database transaction
    as the operation that generated the activity.
    """
    return TodoActivity.objects.create(
        todo=todo,
        actor=actor,
        event_type=event_type,
        description=description,
        metadata=metadata or {},
    )
