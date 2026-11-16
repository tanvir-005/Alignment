from rest_framework import serializers
from .models import Todo, Team


class TodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Todo
        fields = [
            'id',
            'title',
            'description',
            'is_completed',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_title(self, value):
        value = value.strip()

        if not value:
            raise serializers.ValidationError(
                "Title cannot be empty or contain only whitespace."
            )

        return value

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