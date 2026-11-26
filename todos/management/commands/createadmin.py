from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from todos.models import UserProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Create (or promote) the organisation owner/admin account."

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--name", default="Administrator")
        parser.add_argument("--password", help="Prompted for when omitted.")

    def handle(self, *args, **opts):
        email = opts["email"].strip().lower()
        password = opts["password"] or getpass("Password: ")
        try:
            validate_password(password)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages))

        user = User.objects.filter(email__iexact=email).first()
        parts = opts["name"].split()
        if user is None:
            user = User.objects.create_user(
                username=email.split("@")[0],
                email=email,
                password=password,
                first_name=parts[0],
                last_name=" ".join(parts[1:]),
            )
        else:
            user.set_password(password)
            user.save()

        if user.team_memberships.exists():
            raise CommandError(
                "This user belongs to teams. Admins are spectators and cannot be team members."
            )
        UserProfile.objects.update_or_create(
            user=user, defaults={"role": UserProfile.Role.ADMIN}
        )
        self.stdout.write(self.style.SUCCESS(f"Admin ready: {email}"))
