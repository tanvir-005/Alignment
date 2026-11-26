from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import UserProfile

User = get_user_model()


class RegisterSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value.lower()

    @transaction.atomic
    def create(self, validated_data):
        name = validated_data["name"].strip()
        email = validated_data["email"]

        base = email.split("@")[0][:140]
        username, counter = base, 1
        while User.objects.filter(username=username).exists():
            username = f"{base}{counter}"
            counter += 1

        parts = name.split()
        user = User.objects.create_user(
            username=username,
            email=email,
            password=validated_data["password"],
            first_name=parts[0],
            last_name=" ".join(parts[1:]),
        )
        # Everyone who signs up is a plain user; admins are created by the owner
        # (`manage.py createadmin`). Team membership is granted by an admin.
        UserProfile.objects.get_or_create(user=user, defaults={"role": UserProfile.Role.USER})
        return user


class EmailOrUsernameTokenSerializer(TokenObtainPairSerializer):
    """Lets people sign in with their email address (or username)."""

    def validate(self, attrs):
        identifier = attrs.get(self.username_field, "")
        if "@" in identifier:
            match = User.objects.filter(email__iexact=identifier).first()
            if match:
                attrs[self.username_field] = match.get_username()
        return super().validate(attrs)
