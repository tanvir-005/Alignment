from django.contrib import admin

from .models import (
    Notification,
    Team,
    TeamMembership,
    Todo,
    TodoActivity,
    TodoAssignment,
    UserProfile,
)

for model in (
    UserProfile,
    Team,
    TeamMembership,
    Todo,
    TodoAssignment,
    Notification,
    TodoActivity,
):
    admin.site.register(model)
