from django.contrib.auth import get_user_model
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import (
    TEAM_COLORS,
    Notification,
    Team,
    TeamMembership,
    Todo,
    TodoActivity,
)
from .permissions import (
    can_change_status,
    can_edit_todo,
    is_admin,
    is_assignee,
    membership_map,
)
from .utils.names import display_name

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "name", "email"]

    def get_name(self, obj):
        return display_name(obj)


class TeamBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Team
        fields = ["id", "name", "color"]


# ---------------------------------------------------------------- teams
class TeamSerializer(serializers.ModelSerializer):
    """Expects a queryset from selectors.annotated_teams()."""

    pm = serializers.SerializerMethodField()
    member_count = serializers.IntegerField(read_only=True)
    todo_counts = serializers.SerializerMethodField()
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = [
            "id", "name", "description", "color", "created_at",
            "pm", "member_count", "todo_counts", "my_role",
        ]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_pm(self, obj):
        for m in obj.memberships.all():
            if m.role == TeamMembership.Role.PM:
                return UserBriefSerializer(m.user).data
        return None

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_todo_counts(self, obj):
        pending = getattr(obj, "n_pending", 0)
        progress = getattr(obj, "n_in_progress", 0)
        done = getattr(obj, "n_completed", 0)
        return {
            "PENDING": pending,
            "IN_PROGRESS": progress,
            "COMPLETED": done,
            "total": pending + progress + done,
        }

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_my_role(self, obj):
        request = self.context.get("request")
        if not request or is_admin(request.user):
            return None
        return membership_map(request.user).get(obj.id)


class TeamDetailSerializer(TeamSerializer):
    members = serializers.SerializerMethodField()

    class Meta(TeamSerializer.Meta):
        fields = TeamSerializer.Meta.fields + ["members"]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_members(self, obj):
        open_tasks = self.context.get("open_tasks", {})
        rows = []
        for m in obj.memberships.all():
            data = UserBriefSerializer(m.user).data
            data["role"] = m.role
            data["joined_at"] = m.joined_at
            data["open_tasks"] = open_tasks.get(m.user_id, 0)
            rows.append(data)
        rows.sort(key=lambda r: (r["role"] != TeamMembership.Role.PM, r["name"].lower()))
        return rows


class TeamWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    color = serializers.ChoiceField(choices=TEAM_COLORS, required=False)
    pm_id = serializers.IntegerField(required=False)

    def validate_name(self, value):
        value = value.strip()
        qs = Team.objects.filter(name__iexact=value)
        if self.instance is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A team with this name already exists.")
        return value


class AddMembersSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(), allow_empty=False
    )


class ReplacePMSerializer(serializers.Serializer):
    pm_id = serializers.IntegerField()
    old_pm_action = serializers.ChoiceField(
        choices=["member", "remove"], default="member"
    )


# ---------------------------------------------------------------- users
class AdminUserSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "name", "email", "role", "is_active", "date_joined", "memberships",
        ]

    def get_name(self, obj):
        return display_name(obj)

    def get_role(self, obj):
        return "ADMIN" if is_admin(obj) else "USER"

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_memberships(self, obj):
        return [
            {
                "team_id": m.team_id,
                "team_name": m.team.name,
                "team_color": m.team.color,
                "role": m.role,
            }
            for m in obj.team_memberships.all()
        ]


# ---------------------------------------------------------------- todos
class TodoSerializer(serializers.ModelSerializer):
    team = TeamBriefSerializer(read_only=True)
    created_by = UserBriefSerializer(read_only=True)
    assignees = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    can_change_status = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    is_assignee = serializers.SerializerMethodField()

    class Meta:
        model = Todo
        fields = [
            "id", "title", "description", "priority", "due_date", "status",
            "is_overdue", "team", "created_by", "assignees",
            "created_at", "updated_at", "completed_at",
            "can_change_status", "can_edit", "is_assignee",
        ]

    def _user(self):
        return self.context["request"].user

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_assignees(self, obj):
        users = sorted(
            (a.user for a in obj.assignments.all()), key=lambda u: display_name(u).lower()
        )
        return UserBriefSerializer(users, many=True).data

    def get_is_overdue(self, obj):
        return bool(
            obj.due_date
            and obj.status != Todo.Status.COMPLETED
            and obj.due_date < timezone.localdate()
        )

    def get_can_change_status(self, obj):
        return can_change_status(self._user(), obj)

    def get_can_edit(self, obj):
        return can_edit_todo(self._user(), obj)

    def get_is_assignee(self, obj):
        return is_assignee(self._user(), obj)


class TodoCreateSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    title = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=Todo.Priority.choices, default=Todo.Priority.MEDIUM)
    due_date = serializers.DateField(required=False, allow_null=True, default=None)
    assignee_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    all_members = serializers.BooleanField(required=False, default=False)

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        return value


class TodoUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255, required=False)
    description = serializers.CharField(required=False, allow_blank=True)
    priority = serializers.ChoiceField(choices=Todo.Priority.choices, required=False)
    due_date = serializers.DateField(required=False, allow_null=True)
    assignee_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    all_members = serializers.BooleanField(required=False, default=False)

    def validate_title(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Title cannot be blank.")
        return value


class TodoStatusSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Todo.Status.choices)


class TodoActivitySerializer(serializers.ModelSerializer):
    actor = UserBriefSerializer(read_only=True)

    class Meta:
        model = TodoActivity
        fields = ["id", "event_type", "description", "metadata", "actor", "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id", "message", "is_read", "created_at", "todo_id", "team_id", "actor_name",
        ]

    @extend_schema_field(OpenApiTypes.OBJECT)
    def get_actor_name(self, obj):
        return display_name(obj.actor) if obj.actor else None
