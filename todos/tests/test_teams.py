import pytest
from django.db import IntegrityError, transaction

from todos.models import Team, TeamMembership, Todo
from todos.services import team_service

from .helpers import client_for, make_user, new_todo, world  # noqa: F401

pytestmark = pytest.mark.django_db


class TestTeamCreation:
    def test_admin_creates_team_with_pm(self, world):
        r = client_for(world.admin).post(
            "/api/teams/", {"name": "Compass", "pm_id": world.eve.id}, format="json"
        )
        assert r.status_code == 201
        assert r.data["pm"]["id"] == world.eve.id
        assert r.data["member_count"] == 1

    def test_team_without_pm_is_rejected(self, world):
        r = client_for(world.admin).post("/api/teams/", {"name": "NoPM"}, format="json")
        assert r.status_code == 400
        assert not Team.objects.filter(name="NoPM").exists()

    def test_non_admin_cannot_create_team(self, world):
        r = client_for(world.ann).post(
            "/api/teams/", {"name": "X", "pm_id": world.eve.id}, format="json"
        )
        assert r.status_code == 403

    def test_admin_cannot_be_pm(self, world):
        r = client_for(world.admin).post(
            "/api/teams/", {"name": "X", "pm_id": world.admin.id}, format="json"
        )
        assert r.status_code == 400

    def test_duplicate_name_rejected(self, world):
        r = client_for(world.admin).post(
            "/api/teams/", {"name": "atlas", "pm_id": world.eve.id}, format="json"
        )
        assert r.status_code == 400

    def test_db_enforces_single_pm(self, world):
        with pytest.raises(IntegrityError), transaction.atomic():
            TeamMembership.objects.filter(team=world.atlas, user=world.cid).update(role="PM")

    def test_user_can_be_pm_here_and_member_elsewhere(self, world):
        r = client_for(world.ann).get("/api/auth/me/")
        roles = {m["team"]["name"]: m["role"] for m in r.data["memberships"]}
        assert roles == {"Atlas": "PM", "Beacon": "MEMBER"}
        assert r.data["pm_team_ids"] == [world.atlas.id]


class TestVisibility:
    def test_admin_sees_all_teams_member_sees_own(self, world):
        assert len(client_for(world.admin).get("/api/teams/").data) == 2
        names = [t["name"] for t in client_for(world.cid).get("/api/teams/").data]
        assert names == ["Atlas"]

    def test_non_member_gets_404_for_team(self, world):
        assert client_for(world.cid).get(f"/api/teams/{world.beacon.id}/").status_code == 404

    def test_unassigned_user_sees_nothing(self, world):
        c = client_for(world.eve)
        assert c.get("/api/teams/").data == []
        assert c.get("/api/auth/me/").data["has_team"] is False


class TestMembership:
    def test_only_admin_manages_members(self, world):
        r = client_for(world.ann).post(
            f"/api/teams/{world.atlas.id}/members/", {"user_ids": [world.eve.id]}, format="json"
        )
        assert r.status_code == 403
        r = client_for(world.admin).post(
            f"/api/teams/{world.atlas.id}/members/", {"user_ids": [world.eve.id]}, format="json"
        )
        assert r.status_code == 200
        assert r.data["member_count"] == 4

    def test_pm_cannot_remove_members(self, world):
        r = client_for(world.ann).delete(f"/api/teams/{world.atlas.id}/members/{world.cid.id}/")
        assert r.status_code == 403

    def test_pm_cannot_be_removed_directly(self, world):
        r = client_for(world.admin).delete(f"/api/teams/{world.atlas.id}/members/{world.ann.id}/")
        assert r.status_code == 400
        assert world.atlas.memberships.filter(user=world.ann, role="PM").exists()

    def test_remove_member_deletes_sole_assignee_todos_only(self, world):
        solo = new_todo(world.atlas, world.ann, [world.cid], "solo")
        shared = new_todo(world.atlas, world.ann, [world.cid, world.bob], "shared")
        other_team = new_todo(world.beacon, world.bob, [world.dee], "other team")

        impact = client_for(world.admin).get(
            f"/api/teams/{world.atlas.id}/members/{world.cid.id}/impact/"
        )
        assert impact.data == {"is_pm": False, "assigned": 2, "to_delete": 1}

        r = client_for(world.admin).delete(f"/api/teams/{world.atlas.id}/members/{world.cid.id}/")
        assert r.status_code == 200
        assert r.data == {"assigned": 2, "deleted_todos": 1}
        assert not Todo.objects.filter(pk=solo.pk).exists()
        shared.refresh_from_db()
        assert [a.user_id for a in shared.assignments.all()] == [world.bob.id]
        assert Todo.objects.filter(pk=other_team.pk).exists()

    def test_removal_only_affects_that_team(self, world):
        # ann is PM of Atlas and member of Beacon. Removing her from Beacon must
        # not touch her Atlas role or tasks.
        mine_beacon = new_todo(world.beacon, world.bob, [world.ann], "beacon solo")
        mine_atlas = new_todo(world.atlas, world.ann, [world.cid], "atlas")
        team_service.remove_member(actor=world.admin, team=world.beacon, user=world.ann)
        assert not Todo.objects.filter(pk=mine_beacon.pk).exists()
        assert Todo.objects.filter(pk=mine_atlas.pk).exists()
        assert world.atlas.memberships.filter(user=world.ann, role="PM").exists()


class TestReplacePM:
    def test_swap_to_existing_member_demotes_old_pm(self, world):
        r = client_for(world.admin).post(
            f"/api/teams/{world.atlas.id}/replace-pm/", {"pm_id": world.cid.id}, format="json"
        )
        assert r.status_code == 200
        assert r.data["pm"]["id"] == world.cid.id
        roles = {m["id"]: m["role"] for m in r.data["members"]}
        assert roles[world.ann.id] == "MEMBER"
        assert roles[world.cid.id] == "PM"
        assert world.atlas.memberships.filter(role="PM").count() == 1

    def test_swap_to_outsider_adds_them(self, world):
        team_service.replace_pm(actor=world.admin, team=world.atlas, new_pm=world.eve)
        assert world.atlas.memberships.get(user=world.eve).role == "PM"

    def test_old_pm_can_be_removed_and_loses_sole_todos(self, world):
        mine = new_todo(world.atlas, world.ann, [world.ann], "self-assigned")
        team_service.replace_pm(
            actor=world.admin, team=world.atlas, new_pm=world.cid, old_pm_action="remove"
        )
        assert not world.atlas.memberships.filter(user=world.ann).exists()
        assert not Todo.objects.filter(pk=mine.pk).exists()
        assert world.atlas.memberships.filter(role="PM").count() == 1

    def test_same_pm_rejected(self, world):
        r = client_for(world.admin).post(
            f"/api/teams/{world.atlas.id}/replace-pm/", {"pm_id": world.ann.id}, format="json"
        )
        assert r.status_code == 400

    def test_non_admin_cannot_replace(self, world):
        r = client_for(world.ann).post(
            f"/api/teams/{world.atlas.id}/replace-pm/", {"pm_id": world.cid.id}, format="json"
        )
        assert r.status_code == 403


class TestTeamDeleteAndUsers:
    def test_delete_team_cascades(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.admin).delete(f"/api/teams/{world.atlas.id}/")
        assert r.status_code == 204
        assert not Todo.objects.filter(pk=t.pk).exists()
        # Beacon (and ann's membership there) is untouched.
        assert world.beacon.memberships.filter(user=world.ann).exists()

    def test_cannot_deactivate_a_pm(self, world):
        r = client_for(world.admin).post(f"/api/users/{world.ann.id}/deactivate/")
        assert r.status_code == 400

    def test_deactivate_member_removes_from_teams(self, world):
        new_todo(world.atlas, world.ann, [world.cid], "solo")
        r = client_for(world.admin).post(f"/api/users/{world.cid.id}/deactivate/")
        assert r.status_code == 200
        world.cid.refresh_from_db()
        assert not world.cid.is_active
        assert not world.cid.team_memberships.exists()
        assert not Todo.objects.filter(title="solo").exists()

    def test_user_list_admin_only_and_unassigned_filter(self, world):
        assert client_for(world.ann).get("/api/users/").status_code == 403
        r = client_for(world.admin).get("/api/users/?unassigned=true")
        assert [u["email"] for u in r.data["results"]] == ["eve@example.com"]
        r = client_for(world.admin).get(f"/api/users/?exclude_team={world.atlas.id}")
        emails = {u["email"] for u in r.data["results"]}
        assert "ann@example.com" not in emails and "dee@example.com" in emails
