import pytest

from todos.models import Todo

from .helpers import client_for, make_user, new_todo, world  # noqa: F401

pytestmark = pytest.mark.django_db


def payload(team, assignees=None, **extra):
    body = {"team_id": team.id, "title": "Write spec", **extra}
    if assignees is not None:
        body["assignee_ids"] = [u.id for u in assignees]
    return body


class TestCreate:
    def test_pm_creates_and_assigns_multiple(self, world):
        r = client_for(world.ann).post(
            "/api/todos/", payload(world.atlas, [world.bob, world.cid], priority="HIGH"),
            format="json",
        )
        assert r.status_code == 201
        assert {a["id"] for a in r.data["assignees"]} == {world.bob.id, world.cid.id}
        assert r.data["can_edit"] is True and r.data["can_change_status"] is True
        assert r.data["priority"] == "HIGH"

    def test_all_members_flag(self, world):
        r = client_for(world.ann).post(
            "/api/todos/", {"team_id": world.atlas.id, "title": "All", "all_members": True},
            format="json",
        )
        assert r.status_code == 201
        assert len(r.data["assignees"]) == 3  # ann (PM), bob, cid

    def test_member_cannot_create(self, world):
        r = client_for(world.cid).post(
            "/api/todos/", payload(world.atlas, [world.cid]), format="json"
        )
        assert r.status_code == 403

    def test_pm_of_other_team_cannot_create_here(self, world):
        # bob is PM of Beacon but only a member of Atlas
        r = client_for(world.bob).post(
            "/api/todos/", payload(world.atlas, [world.cid]), format="json"
        )
        assert r.status_code == 403

    def test_admin_cannot_create(self, world):
        r = client_for(world.admin).post(
            "/api/todos/", payload(world.atlas, [world.cid]), format="json"
        )
        assert r.status_code == 403

    def test_assignee_must_be_team_member(self, world):
        r = client_for(world.ann).post(
            "/api/todos/", payload(world.atlas, [world.dee]), format="json"
        )
        assert r.status_code == 400

    def test_needs_at_least_one_assignee(self, world):
        r = client_for(world.ann).post("/api/todos/", payload(world.atlas, []), format="json")
        assert r.status_code == 400

    def test_pm_can_assign_self(self, world):
        r = client_for(world.ann).post(
            "/api/todos/", payload(world.atlas, [world.ann]), format="json"
        )
        assert r.status_code == 201


class TestStatus:
    def test_any_assignee_can_change_status(self, world):
        t = new_todo(world.atlas, world.ann, [world.bob, world.cid])
        for user, new in ((world.bob, "IN_PROGRESS"), (world.cid, "COMPLETED")):
            r = client_for(user).patch(f"/api/todos/{t.id}/status/", {"status": new}, format="json")
            assert r.status_code == 200 and r.data["status"] == new
        t.refresh_from_db()
        assert t.completed_at is not None

    def test_reopening_clears_completed_at(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        c = client_for(world.cid)
        c.patch(f"/api/todos/{t.id}/status/", {"status": "COMPLETED"}, format="json")
        c.patch(f"/api/todos/{t.id}/status/", {"status": "PENDING"}, format="json")
        t.refresh_from_db()
        assert t.completed_at is None

    def test_pm_can_change_status_without_being_assignee(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.ann).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        assert r.status_code == 200

    def test_non_assignee_member_cannot(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.bob).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        assert r.status_code == 403
        assert client_for(world.bob).get(f"/api/todos/{t.id}/").data["can_change_status"] is False

    def test_admin_cannot(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.admin).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        assert r.status_code == 403

    def test_outsider_gets_404(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.dee).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        assert r.status_code == 404

    def test_pm_of_other_team_has_no_power_here(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.bob).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        assert r.status_code == 403

    def test_status_change_is_logged_and_notifies(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        client_for(world.cid).patch(
            f"/api/todos/{t.id}/status/", {"status": "IN_PROGRESS"}, format="json"
        )
        acts = client_for(world.ann).get(f"/api/todos/{t.id}/activities/").data
        assert acts[0]["event_type"] == "STATUS_CHANGED"
        assert world.ann.notifications.filter(message__contains="In progress").exists()


class TestEditDelete:
    def test_only_pm_edits(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        assert client_for(world.cid).patch(
            f"/api/todos/{t.id}/", {"title": "Hack"}, format="json"
        ).status_code == 403
        r = client_for(world.ann).patch(
            f"/api/todos/{t.id}/", {"title": "Renamed", "priority": "LOW"}, format="json"
        )
        assert r.status_code == 200 and r.data["title"] == "Renamed"

    def test_reassign_via_patch(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.ann).patch(
            f"/api/todos/{t.id}/", {"assignee_ids": [world.bob.id]}, format="json"
        )
        assert [a["id"] for a in r.data["assignees"]] == [world.bob.id]
        assert world.cid.notifications.filter(message__contains="unassigned").exists()

    def test_cannot_empty_assignees(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        r = client_for(world.ann).patch(f"/api/todos/{t.id}/", {"assignee_ids": []}, format="json")
        assert r.status_code == 400

    def test_only_pm_deletes(self, world):
        t = new_todo(world.atlas, world.ann, [world.cid])
        assert client_for(world.cid).delete(f"/api/todos/{t.id}/").status_code == 403
        assert client_for(world.admin).delete(f"/api/todos/{t.id}/").status_code == 403
        assert client_for(world.ann).delete(f"/api/todos/{t.id}/").status_code == 204
        assert not Todo.objects.filter(pk=t.pk).exists()


class TestListing:
    @pytest.fixture
    def data(self, world):
        w = world
        w.mine = new_todo(w.atlas, w.ann, [w.cid], "cid task")           # actionable for cid
        w.other = new_todo(w.atlas, w.ann, [w.bob], "bob task")          # other for cid
        w.beacon_task = new_todo(w.beacon, w.bob, [w.dee], "dee task")   # invisible to cid
        w.ann_beacon = new_todo(w.beacon, w.bob, [w.ann], "ann in beacon")
        return w

    def ids(self, client, qs=""):
        return {t["id"] for t in client.get(f"/api/todos/{qs}").data["results"]}

    def test_member_sees_only_own_team_todos(self, data):
        assert self.ids(client_for(data.cid)) == {data.mine.id, data.other.id}

    def test_actionable_vs_other(self, data):
        c = client_for(data.cid)
        assert self.ids(c, "?scope=actionable") == {data.mine.id}
        assert self.ids(c, "?scope=other") == {data.other.id}

    def test_pm_actionable_includes_whole_managed_team_plus_own_assignments(self, data):
        # ann is PM of Atlas (2 todos) and assigned to a Beacon todo
        ids = self.ids(client_for(data.ann), "?scope=actionable")
        assert ids == {data.mine.id, data.other.id, data.ann_beacon.id}
        # the other Beacon todo (assigned to dee) is visible but not actionable
        other = self.ids(client_for(data.ann), "?scope=other")
        assert other == {data.beacon_task.id}

    def test_actionable_matches_can_change_status_flag(self, data):
        for user in (data.ann, data.bob, data.cid, data.dee):
            c = client_for(user)
            rows = c.get("/api/todos/?limit=100").data["results"]
            flagged = {t["id"] for t in rows if t["can_change_status"]}
            assert flagged == self.ids(c, "?scope=actionable")

    def test_team_filter(self, data):
        ids = self.ids(client_for(data.ann), f"?team={data.beacon.id}")
        assert ids == {data.beacon_task.id, data.ann_beacon.id}

    def test_admin_sees_all_with_no_actions(self, data):
        c = client_for(data.admin)
        rows = c.get("/api/todos/?limit=100").data["results"]
        assert len(rows) == 4
        assert not any(t["can_change_status"] or t["can_edit"] for t in rows)
        assert self.ids(c, "?scope=actionable") == set()

    def test_unassigned_user_sees_nothing(self, data):
        assert self.ids(client_for(data.eve)) == set()

    def test_search_status_priority_filters(self, data):
        c = client_for(data.admin)
        assert self.ids(c, "?search=dee") == {data.beacon_task.id}
        client_for(data.cid).patch(
            f"/api/todos/{data.mine.id}/status/", {"status": "COMPLETED"}, format="json"
        )
        assert self.ids(c, "?status=COMPLETED") == {data.mine.id}

    def test_detail_404_for_outsider(self, data):
        assert client_for(data.cid).get(f"/api/todos/{data.beacon_task.id}/").status_code == 404
