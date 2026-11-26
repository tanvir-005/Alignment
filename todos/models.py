from django.conf import settings
from django.db import models
from django.db.models import Q

# Keys are mapped to hex values in the frontend (src/lib/teamColors.js).
TEAM_COLORS = ["blue", "teal", "green", "amber", "orange", "rose", "violet", "slate"]


class UserProfile(models.Model):
    """Global role only. Being a PM is a per-team property (TeamMembership)."""

    class Role(models.TextChoices):
        USER = "USER", "User"
        ADMIN = "ADMIN", "Admin"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.USER)

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class Team(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(
        max_length=12,
        choices=[(c, c.title()) for c in TEAM_COLORS],
        default="blue",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeamMembership(models.Model):
    """
    A user's place in a team. Exactly one membership per team has role PM
    (enforced by a partial unique constraint + the team service layer).
    A user may belong to many teams, and be PM in some and member in others.
    """

    class Role(models.TextChoices):
        MEMBER = "MEMBER", "Member"
        PM = "PM", "Project manager"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
    )
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.MEMBER)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_member"),
            models.UniqueConstraint(
                fields=["team"],
                condition=Q(role="PM"),
                name="one_pm_per_team",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} in {self.team_id} as {self.role}"


class Todo(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        COMPLETED = "COMPLETED", "Completed"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="todos")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_todos",
    )
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=15, choices=Status.choices, default=Status.PENDING
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    assignees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="TodoAssignment",
        through_fields=("todo", "user"),
        related_name="assigned_todos",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.title


class TodoAssignment(models.Model):
    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="assignments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="todo_assignments",
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["todo", "user"], name="unique_todo_assignee"),
        ]

    def __str__(self):
        return f"todo {self.todo_id} -> user {self.user_id}"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_notifications",
    )
    # Both nullable so a notification outlives a deleted todo / team.
    todo = models.ForeignKey(
        Todo, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    team = models.ForeignKey(
        Team, on_delete=models.SET_NULL, null=True, blank=True, related_name="notifications"
    )
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return self.message


class TodoActivity(models.Model):
    class EventType(models.TextChoices):
        CREATED = "CREATED", "Created"
        UPDATED = "UPDATED", "Updated"
        ASSIGNEES_CHANGED = "ASSIGNEES_CHANGED", "Assignees changed"
        STATUS_CHANGED = "STATUS_CHANGED", "Status changed"

    todo = models.ForeignKey(Todo, on_delete=models.CASCADE, related_name="activities")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="todo_activities",
    )
    event_type = models.CharField(max_length=32, choices=EventType.choices)
    description = models.CharField(max_length=255)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"{self.event_type}: {self.todo_id}"


class TodoDeletion(models.Model):
    """
    Tombstone for a deleted todo. Deleting a todo cascades its activity rows, so
    without this the daily digest could not report that it was deleted.
    """

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="deletions")
    title = models.CharField(max_length=255)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    reason = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]


class DigestLog(models.Model):
    """One row per team per day: guarantees the daily digest is sent only once."""

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="digests")
    date = models.DateField()
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    event_count = models.PositiveIntegerField(default=0)
    sent_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["team", "date"], name="one_digest_per_team_per_day"),
        ]
