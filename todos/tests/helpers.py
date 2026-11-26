import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from todos.models import Team, TeamMembership, Todo, TodoAssignment, UserProfile
from todos.services import team_service, todo_service

User = get_user_model()


def make_user(name, admin=False):
    first = name.split()[0].lower()
    user = User.objects.create_user(
        username=first, email=f"{first}@example.com", password="Pass@12345x",
        first_name=name.split()[0], last_name=" ".join(name.split()[1:]),
    )
    if admin:
        UserProfile.objects.filter(user=user).update(role=UserProfile.Role.ADMIN)
        user = User.objects.get(pk=user.pk)
    return user


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c


@pytest.fixture
def world(db):
    """
    admin
    Atlas : PM=ann,  members=bob, cid
    Beacon: PM=bob,  members=ann, dee
    eve   : signed up, no team
    """
    w = type("World", (), {})()
    w.admin = make_user("Root Admin", admin=True)
    w.ann, w.bob, w.cid, w.dee, w.eve = (
        make_user(n) for n in ("Ann A", "Bob B", "Cid C", "Dee D", "Eve E")
    )
    w.atlas = team_service.create_team(actor=w.admin, name="Atlas", pm=w.ann)
    w.beacon = team_service.create_team(actor=w.admin, name="Beacon", pm=w.bob)
    team_service.add_members(actor=w.admin, team=w.atlas, users=[w.bob, w.cid])
    team_service.add_members(actor=w.admin, team=w.beacon, users=[w.ann, w.dee])
    return w


def new_todo(team, pm, assignees, title="Task", **kw):
    return todo_service.create_todo(
        actor=pm, team=team, title=title, assignee_ids=[u.id for u in assignees], **kw
    )
