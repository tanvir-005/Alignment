import pytest
from django.contrib.auth import get_user_model

from todos.models import UserProfile

from .helpers import client_for, make_user, new_todo, world  # noqa: F401
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db
User = get_user_model()


class TestAuth:
    def test_register_creates_plain_user_never_admin(self):
        c = APIClient()
        r = c.post(
            "/api/auth/register/",
            {"name": "New Person", "email": "new@example.com", "password": "Str0ng!Pass#9"},
            format="json",
        )
        assert r.status_code == 201
        u = User.objects.get(email="new@example.com")
        assert u.profile.role == UserProfile.Role.USER
        # even the very first user is not an admin
        assert not UserProfile.objects.filter(role="ADMIN").exists()

    def test_duplicate_email_message_is_returned(self):
        make_user("Dup One")
        r = APIClient().post(
            "/api/auth/register/",
            {"name": "Dup Two", "email": "dup@example.com", "password": "Str0ng!Pass#9"},
            format="json",
        )
        assert r.status_code == 400
        assert "already registered" in r.data["error"]

    def test_login_with_email(self):
        make_user("Login User")
        r = APIClient().post(
            "/api/auth/login/", {"username": "login@example.com", "password": "Pass@12345x"},
            format="json",
        )
        assert r.status_code == 200 and "access" in r.data

    def test_me_for_admin(self, world):
        r = client_for(world.admin).get("/api/auth/me/")
        assert r.data["is_admin"] is True and r.data["memberships"] == []

    def test_unauthenticated_blocked(self, world):
        assert APIClient().get("/api/todos/").status_code == 401


class TestNotifications:
    def test_assignment_notifies_assignee_not_actor(self, world):
        new_todo(world.atlas, world.ann, [world.cid, world.ann], "Hello")
        assert world.cid.notifications.count() >= 1
        assert not world.ann.notifications.filter(message__contains="assigned you").exists()

    def test_read_and_count(self, world):
        new_todo(world.atlas, world.ann, [world.cid])
        c = client_for(world.cid)
        before = c.get("/api/notifications/unread-count/").data["unread_count"]
        assert before >= 1
        nid = c.get("/api/notifications/").data["results"][0]["id"]
        c.patch(f"/api/notifications/{nid}/read/")
        assert c.get("/api/notifications/unread-count/").data["unread_count"] == before - 1
        c.patch("/api/notifications/read-all/")
        assert c.get("/api/notifications/unread-count/").data["unread_count"] == 0

    def test_cannot_read_others_notification(self, world):
        new_todo(world.atlas, world.ann, [world.cid])
        nid = world.cid.notifications.first().id
        assert client_for(world.bob).patch(f"/api/notifications/{nid}/read/").status_code == 404

    def test_notification_survives_todo_deletion(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        client_for(world.ann).delete(f"/api/todos/{t.id}/")
        assert world.cid.notifications.filter(message__contains="deleted").exists()


class TestAdminOverview:
    def test_overview_numbers(self, world):
        new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.admin).get("/api/admin/overview/")
        assert r.status_code == 200
        t = r.data["totals"]
        assert t["teams"] == 2 and t["unassigned_users"] == 1 and t["todos"] == 1
        assert r.data["status_counts"]["PENDING"] == 1
        assert len(r.data["teams"]) == 2

    def test_overview_is_admin_only(self, world):
        assert client_for(world.ann).get("/api/admin/overview/").status_code == 403
