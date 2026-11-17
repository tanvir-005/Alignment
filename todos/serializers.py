from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Todo, Team, UserProfile, Notification


class TodoSerializer(serializers.ModelSerializer):
    creator = serializers.IntegerField(
        source="user_id",
        read_only=True
    )

    assignee = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    team = serializers.PrimaryKeyRelatedField(
        read_only=True
    )

    is_completed = serializers.BooleanField(read_only=True)

    class Meta:
        model = Todo
        fields = [
            "id",
            "creator",
            "assignee",
            "team",
            "title",
            "description",
            "task_status",
            "assignment_status",
            "is_completed",
            "created_at",
            "updated_at",
        ]

        read_only_fields = [
            "id",
            "creator",
            "assignee",
            "team",
            "assignment_status",
            "is_completed",
            "created_at",
            "updated_at",
        ]

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Title cannot be empty or contain only whitespace."
            )

        return value

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)

        instance.is_completed = (
            instance.task_status == Todo.TaskStatus.COMPLETED
        )
        instance.save(update_fields=["is_completed"])

        return instance

class TeamSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "description", "members"]

    def get_members(self, obj):
        profiles = obj.members.select_related("user").all()

        return [
            {
                "id": profile.user.id,
                "username": profile.user.username,
                "first_name": profile.user.first_name,
                "last_name": profile.user.last_name,
                "role": profile.role,
            }
            for profile in profiles
        ]

class UserListSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    team = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "team",
        ]

    def get_team(self, obj):
        team = obj.profile.team

        if not team:
            return None

        return {
            "id": team.id,
            "name": team.name,
        }

class UserAdminUpdateSerializer(serializers.Serializer):
    role = serializers.ChoiceField(
        choices=UserProfile.Role.choices,
        required=False
    )

    team = serializers.PrimaryKeyRelatedField(
        queryset=Team.objects.all(),
        required=False,
        allow_null=True
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError(
                "Provide at least one field to update."
            )
        return attrs

class TodoAssignmentSerializer(serializers.Serializer):
    assignee = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(is_active=True)
    )

class TodoAssignmentResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            Todo.AssignmentStatus.ACCEPTED,
            Todo.AssignmentStatus.REJECTED,
        ]
    )

class NotificationSerializer(serializers.ModelSerializer):
    actor = serializers.CharField(
        source="actor.username",
        read_only=True,
        default=None,
    )
    todo_title = serializers.CharField(
        source="todo.title",
        read_only=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "actor",
            "todo",
            "todo_title",
            "message",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields