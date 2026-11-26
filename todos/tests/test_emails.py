from datetime import timedelta
from io import StringIO
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from django.db import transaction
from django.utils import timezone

from todos.models import DigestLog, TodoActivity
from todos.services import team_service, todo_service

from .helpers import client_for, make_user, new_todo, world  # noqa: F401

pytestmark = pytest.mark.django_db


@pytest.fixture
def commit(django_capture_on_commit_callbacks):
    """Run on_commit hooks (emails) as a real commit would."""
    from contextlib import contextmanager

    @contextmanager
    def run():
        with django_capture_on_commit_callbacks(execute=True):
            yield

    return run


class TestAssignmentEmail:
    def test_new_assignees_get_an_email_with_the_task(self, world, commit, mailoutbox):
        with commit():
            new_todo(
                world.atlas, world.ann, [world.bob, world.cid], "Write spec",
                description="Cover the API.", priority="HIGH",
            )
        assert sorted(m.to[0] for m in mailoutbox) == ["bob@example.com", "cid@example.com"]
        m = mailoutbox[0]
        assert "Write spec" in m.subject and "Atlas" in m.subject
        assert "Cover the API." in m.body and "High" in m.body
        assert "/todos/" in m.body
        assert m.alternatives and "Open task" in m.alternatives[0][0]

    def test_pm_is_not_emailed_about_assigning_themselves(self, world, commit, mailoutbox):
        with commit():
            new_todo(world.atlas, world.ann, [world.ann, world.cid])
        assert [m.to[0] for m in mailoutbox] == ["cid@example.com"]

    def test_reassigning_emails_only_the_newly_added(self, world, commit, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        with commit():
            todo_service.update_todo(
                actor=world.ann, todo=t, assignee_ids=[world.cid.id, world.bob.id]
            )
        assert [m.to[0] for m in mailoutbox] == ["bob@example.com"]

    def test_title_edit_alone_sends_no_assignment_email(self, world, commit, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        with commit():
            todo_service.update_todo(actor=world.ann, todo=t, title="New title")
        assert mailoutbox == []

    def test_nothing_is_sent_if_the_transaction_rolls_back(self, world, commit, mailoutbox):
        with commit():
            try:
                with transaction.atomic():
                    new_todo(world.atlas, world.ann, [world.cid])
                    raise RuntimeError("boom")
            except RuntimeError:
                pass
        assert mailoutbox == []

    def test_mail_failure_does_not_break_the_api(self, world, commit):
        c = client_for(world.ann)
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("smtp down")):
            with commit():
                r = c.post(
                    "/api/todos/",
                    {"team_id": world.atlas.id, "title": "Still created", "assignee_ids": [world.cid.id]},
                    format="json",
                )
        assert r.status_code == 201


class TestStatusEmail:
    def test_pm_is_emailed_when_an_assignee_changes_status(self, world, commit, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        with commit():
            todo_service.change_status(actor=world.cid, todo=t, status="IN_PROGRESS")
        assert len(mailoutbox) == 1
        m = mailoutbox[0]
        assert m.to == ["ann@example.com"]
        assert "In progress" in m.subject
        assert "Pending" in m.body and "In progress" in m.body and "Cid" in m.body

    def test_pm_is_not_emailed_about_their_own_change(self, world, commit, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        with commit():
            todo_service.change_status(actor=world.ann, todo=t, status="COMPLETED")
        assert mailoutbox == []

    def test_unchanged_status_sends_nothing(self, world, commit, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        with commit():
            todo_service.change_status(actor=world.cid, todo=t, status="PENDING")
        assert mailoutbox == []

    def test_only_the_todos_own_team_pm_is_emailed(self, world, commit, mailoutbox):
        # bob is PM of Beacon but just a member of Atlas
        t = new_todo(world.atlas, world.ann, [world.bob])
        mailoutbox.clear()
        with commit():
            todo_service.change_status(actor=world.bob, todo=t, status="COMPLETED")
        assert [m.to[0] for m in mailoutbox] == ["ann@example.com"]


def run_digest(*args):
    out = StringIO()
    call_command("send_daily_digest", *args, stdout=out)
    return out.getvalue()


class TestDailyDigest:
    def test_each_pm_gets_only_their_team(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid], "Atlas task")
        new_todo(world.beacon, world.bob, [world.dee], "Beacon task")
        mailoutbox.clear()
        run_digest()
        by_to = {m.to[0]: m for m in mailoutbox}
        assert set(by_to) == {"ann@example.com", "bob@example.com"}
        assert "Atlas task" in by_to["ann@example.com"].body
        assert "Beacon task" not in by_to["ann@example.com"].body
        assert "Beacon task" in by_to["bob@example.com"].body
        assert "Daily summary" in by_to["ann@example.com"].subject

    def test_quiet_teams_get_nothing(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        out = run_digest()
        assert [m.to[0] for m in mailoutbox] == ["ann@example.com"]
        assert "Beacon" in out and "no activity" in out

    def test_only_the_last_24_hours_count(self, world, mailoutbox):
        old = new_todo(world.atlas, world.ann, [world.cid], "Ancient")
        TodoActivity.objects.filter(todo=old).update(created_at=timezone.now() - timedelta(hours=30))
        new_todo(world.atlas, world.ann, [world.cid], "Fresh")
        mailoutbox.clear()
        run_digest()
        body = mailoutbox[0].body
        assert "Fresh" in body and "Ancient" not in body

    def test_summarises_status_changes_and_counts(self, world, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid], "Ship it")
        todo_service.change_status(actor=world.cid, todo=t, status="IN_PROGRESS")
        todo_service.change_status(actor=world.cid, todo=t, status="COMPLETED")
        mailoutbox.clear()
        run_digest()
        body = mailoutbox[0].body
        assert "Created: 1" in body and "Status changes: 2" in body and "Completed: 1" in body
        assert "moved this from" in body

    def test_deleted_tasks_are_reported(self, world, mailoutbox):
        t = new_todo(world.atlas, world.ann, [world.cid], "Doomed task")
        todo_service.delete_todo(actor=world.ann, todo=t)
        mailoutbox.clear()
        run_digest()
        assert "Doomed task" in mailoutbox[0].body and "deleted" in mailoutbox[0].body

    def test_tasks_deleted_by_member_removal_are_reported(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid], "Cid only")
        team_service.remove_member(actor=world.admin, team=world.atlas, user=world.cid)
        mailoutbox.clear()
        run_digest()
        body = mailoutbox[0].body
        assert "Cid only" in body and "removed from the team" in body

    def test_runs_once_per_day_unless_forced(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid])
        mailoutbox.clear()
        run_digest()
        run_digest()
        assert len(mailoutbox) == 1
        assert DigestLog.objects.filter(team=world.atlas).count() == 1
        run_digest("--force")
        assert len(mailoutbox) == 2
        assert DigestLog.objects.filter(team=world.atlas).count() == 1

    def test_dry_run_sends_and_logs_nothing(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid], "Dry task")
        mailoutbox.clear()
        out = run_digest("--dry-run")
        assert mailoutbox == [] and DigestLog.objects.count() == 0
        assert "Dry task" in out

    def test_pm_of_two_teams_gets_two_emails(self, world, mailoutbox):
        team_service.replace_pm(actor=world.admin, team=world.beacon, new_pm=world.ann)
        new_todo(world.atlas, world.ann, [world.cid], "A")
        new_todo(world.beacon, world.ann, [world.dee], "B")
        mailoutbox.clear()
        run_digest()
        mine = [m for m in mailoutbox if m.to == ["ann@example.com"]]
        assert len(mine) == 2
        assert {("Atlas" in m.subject, "Beacon" in m.subject) for m in mine} == {(True, False), (False, True)}

    def test_send_failure_is_reported_and_not_logged(self, world, mailoutbox):
        new_todo(world.atlas, world.ann, [world.cid])
        with mock.patch("django.core.mail.EmailMultiAlternatives.send", side_effect=OSError("down")):
            out = run_digest()
        assert "FAILED" in out and DigestLog.objects.count() == 0
        out = run_digest()  # next run retries
        assert DigestLog.objects.count() == 1
