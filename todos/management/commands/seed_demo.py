from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from todos.models import Team, UserProfile
from todos.services import team_service, todo_service

User = get_user_model()

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin@2026Demo"
USER_PASSWORD = "Demo@2026Pass"


class Command(BaseCommand):
    help = "Create a demo organisation: 1 admin, 3 teams, PMs, members and tasks."

    @transaction.atomic
    def handle(self, *args, **options):
        if Team.objects.exists():
            self.stdout.write("Demo data already present - nothing to do.")
            return

        admin = self._user("Olivia Owner", ADMIN_EMAIL, ADMIN_PASSWORD, admin=True)

        people = {
            key: self._user(name, f"{key}@example.com", USER_PASSWORD)
            for key, name in {
                "priya": "Priya Nair",
                "omar": "Omar Haddad",
                "lena": "Lena Fischer",
                "jonas": "Jonas Weber",
                "mei": "Mei Tanaka",
                "sam": "Sam Rivera",
                "ana": "Ana Costa",
                "tomas": "Tomas Novak",
            }.items()
        }

        atlas = team_service.create_team(
            actor=admin, name="Atlas · Website", color="blue", pm=people["priya"],
            description="Marketing website relaunch.",
        )
        beacon = team_service.create_team(
            actor=admin, name="Beacon · Mobile", color="orange", pm=people["omar"],
            description="Customer mobile app.",
        )
        compass = team_service.create_team(
            actor=admin, name="Compass · Operations", color="teal", pm=people["lena"],
            description="Internal tooling and operations.",
        )

        team_service.add_members(
            actor=admin, team=atlas,
            users=[people["omar"], people["jonas"], people["mei"], people["ana"]],
        )
        team_service.add_members(
            actor=admin, team=beacon,
            users=[people["priya"], people["jonas"], people["tomas"]],
        )
        team_service.add_members(
            actor=admin, team=compass, users=[people["mei"], people["tomas"]],
        )
        # `sam` signed up but has not been added anywhere yet.

        today = timezone.localdate()
        P = people

        def todo(team, pm, title, desc, who, priority="MEDIUM", due=None, status=None):
            t = todo_service.create_todo(
                actor=pm, team=team, title=title, description=desc,
                priority=priority, due_date=due, assignee_ids=[u.id for u in who],
            )
            if status:
                todo_service.change_status(actor=who[0], todo=t, status=status)
            return t

        todo(atlas, P["priya"], "Design new homepage hero", "Three concepts for review.",
             [P["mei"]], "HIGH", today + timedelta(days=3), "IN_PROGRESS")
        todo(atlas, P["priya"], "Migrate blog content", "Move posts to the new CMS.",
             [P["jonas"], P["ana"]], "MEDIUM", today + timedelta(days=10))
        todo(atlas, P["priya"], "Accessibility audit", "WCAG 2.2 AA pass on key pages.",
             [P["omar"]], "HIGH", today - timedelta(days=2))
        todo(atlas, P["priya"], "Write launch announcement", "Draft + legal review.",
             [P["ana"]], "LOW", today + timedelta(days=14), "COMPLETED")
        todo(beacon, P["omar"], "Push notification service", "Integrate provider SDK.",
             [P["jonas"]], "HIGH", today + timedelta(days=5), "IN_PROGRESS")
        todo(beacon, P["omar"], "Onboarding flow QA", "Test on iOS and Android.",
             [P["tomas"], P["priya"]], "MEDIUM", today + timedelta(days=7))
        todo(beacon, P["omar"], "App store listing copy", "Screenshots and descriptions.",
             [P["priya"]], "LOW", None, "COMPLETED")
        todo(compass, P["lena"], "Automate weekly report", "Pull metrics into a dashboard.",
             [P["mei"], P["tomas"]], "MEDIUM", today + timedelta(days=6))
        todo(compass, P["lena"], "Vendor contract review", "Renewals due this quarter.",
             [P["lena"]], "HIGH", today + timedelta(days=2), "IN_PROGRESS")

        self.stdout.write(self.style.SUCCESS("Demo data created."))
        self.stdout.write(f"  Admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        self.stdout.write(f"  Users: priya@ omar@ lena@ jonas@ mei@ sam@ ana@ tomas@example.com / {USER_PASSWORD}")
        self.stdout.write("  Priya is PM of Atlas and a member of Beacon; Omar is the reverse.")
        self.stdout.write("  Sam has no team yet - add them from Admin > Users.")

    def _user(self, name, email, password, admin=False):
        parts = name.split()
        user = User.objects.create_user(
            username=email.split("@")[0], email=email, password=password,
            first_name=parts[0], last_name=" ".join(parts[1:]),
        )
        if admin:
            UserProfile.objects.filter(user=user).update(role=UserProfile.Role.ADMIN)
        return user
