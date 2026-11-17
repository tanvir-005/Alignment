
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from todos.models import Team, UserProfile, Todo


User = get_user_model()


class Command(BaseCommand):
    help = "Create predefined teams and demo users/todos."

    def handle(self, *args, **options):
        self.stdout.write("Seeding demo data...")

        # 1. Create predefined teams.
        alpha, _ = Team.objects.get_or_create(
            name="Team Alpha",
            defaults={"description": "Primary demo team."},
        )

        beta, _ = Team.objects.get_or_create(
            name="Team Beta",
            defaults={"description": "Secondary demo team."},
        )

        self.stdout.write(self.style.SUCCESS("Teams ready."))

        # 2. Find an existing admin. If none exists, create one.
        admin_profile = (
            UserProfile.objects
            .filter(role=UserProfile.Role.ADMIN)
            .select_related("user")
            .first()
        )

        if admin_profile:
            admin = admin_profile.user
        else:
            admin, created = User.objects.get_or_create(
                username="demo_admin",
                defaults={"email": "admin@example.com"},
            )

            if created:
                admin.set_password("Admin@2026Demo")
                admin.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=admin,
                defaults={"role": UserProfile.Role.ADMIN},
            )
            profile.role = UserProfile.Role.ADMIN
            profile.save(update_fields=["role"])

        # 3. Create demo members.
        demo_members = [
            {
                "username": "alice",
                "email": "alice@example.com",
                "password": "Alice@2026Secure",
                "team": alpha,
            },
            {
                "username": "bob",
                "email": "bob@example.com",
                "password": "Bob@2026Secure",
                "team": alpha,
            },
            {
                "username": "charlie",
                "email": "charlie@example.com",
                "password": "Charlie@2026Secure",
                "team": beta,
            },
        ]

        members = {}

        for item in demo_members:
            user, created = User.objects.get_or_create(
                username=item["username"],
                defaults={"email": item["email"]},
            )

            if created:
                user.set_password(item["password"])
                user.save()

            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    "role": UserProfile.Role.MEMBER,
                    "team": item["team"],
                },
            )

            # Only assign a team when the user has none.
            if profile.team is None:
                profile.team = item["team"]
                profile.save(update_fields=["team"])

            members[item["username"]] = user

        # 4. Assign the admin to Team Alpha only if unassigned.
        admin_profile = admin.profile

        if admin_profile.team is None:
            admin_profile.team = alpha
            admin_profile.save(update_fields=["team"])

        self.stdout.write(self.style.SUCCESS("Demo users ready."))

        # 5. Create sample todos without duplicating them.
        alice = members["alice"]
        bob = members["bob"]

        Todo.objects.get_or_create(
            user=admin,
            title="Prepare programming workshop",
            defaults={
                "description": "Prepare materials for the programming workshop.",
                "team": alpha,
                "assignee": alice,
                "task_status": Todo.TaskStatus.PENDING,
                "assignment_status": Todo.AssignmentStatus.PENDING,
            },
        )

        Todo.objects.get_or_create(
            user=alice,
            title="Review workshop problems",
            defaults={
                "description": "Review the selected programming problems.",
                "team": alpha,
                "assignee": bob,
                "task_status": Todo.TaskStatus.PENDING,
                "assignment_status": Todo.AssignmentStatus.PENDING,
            },
        )

        self.stdout.write(self.style.SUCCESS("Sample todos ready."))
        self.stdout.write(self.style.SUCCESS("Demo seeding completed."))
