from django.core.management.base import BaseCommand
from django.template import Context
from django.template.loader import get_template
from django.utils import timezone

from todos.models import DigestLog, Team, TeamMembership
from todos.services import digest_service


class Command(BaseCommand):
    help = (
        "Email each team's PM a summary of the last 24 hours. "
        "Schedule it for 22:00 (see README). Safe to re-run: one digest per team per day."
    )

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=24, help="Window length (default 24).")
        parser.add_argument("--dry-run", action="store_true", help="Print instead of sending.")
        parser.add_argument("--force", action="store_true", help="Ignore the once-per-day log.")
        parser.add_argument("--team", type=int, help="Only this team id.")

    def handle(self, *args, **opts):
        since, until = digest_service.default_window(opts["hours"])
        today = timezone.localdate(until)
        teams = Team.objects.all().order_by("name")
        if opts["team"]:
            teams = teams.filter(pk=opts["team"])

        sent = skipped = failed = 0
        for team in teams:
            pm_membership = (
                TeamMembership.objects.filter(team=team, role=TeamMembership.Role.PM)
                .select_related("user")
                .first()
            )
            if not pm_membership or not pm_membership.user.email:
                self.stdout.write(f"- {team.name}: no PM email, skipped")
                skipped += 1
                continue
            if not opts["force"] and not opts["dry_run"] and DigestLog.objects.filter(
                team=team, date=today
            ).exists():
                self.stdout.write(f"- {team.name}: already sent today, skipped")
                skipped += 1
                continue

            context = digest_service.build_digest(team=team, since=since, until=until)
            if context is None:
                self.stdout.write(f"- {team.name}: no activity, skipped")
                skipped += 1
                continue

            pm = pm_membership.user
            if opts["dry_run"]:
                body = get_template("email/daily_digest.txt").template.render(
                    Context({**context, "recipient_name": pm.get_full_name() or pm.username}, autoescape=False)
                )
                self.stdout.write(f"\n--- DRY RUN: {team.name} -> {pm.email} ---\n{body}")
                continue

            if digest_service.send_digest(team=team, pm=pm, context=context, until=until):
                self.stdout.write(self.style.SUCCESS(f"- {team.name}: sent to {pm.email}"))
                sent += 1
            else:
                self.stdout.write(self.style.ERROR(f"- {team.name}: FAILED for {pm.email}"))
                failed += 1

        self.stdout.write(f"Done. sent={sent} skipped={skipped} failed={failed}")
