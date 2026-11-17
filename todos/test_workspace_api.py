
import pytest

from django.contrib.auth.models import User
from rest_framework.test import APIClient

from todos.models import Team, UserProfile, Todo, Notification


# -------------------------------------------------------------------
# Fixtures
# -------------------------------------------------------------------

@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def team(db):
    return Team.objects.create(name="Workspace Test Team")


@pytest.fixture
def other_team(db):
    return Team.objects.create(name="Other Test Team")


@pytest.fixture
def member(db, team):
    user = User.objects.create_user(
        username="workspace_member",
        email="member@test.com",
        password="StrongPassword123!"
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.MEMBER,
        team=team
    )
    return user


@pytest.fixture
def admin(db, team):
    user = User.objects.create_user(
        username="workspace_admin",
        email="admin@test.com",
        password="StrongPassword123!"
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.ADMIN,
        team=team
    )
    return user


@pytest.fixture
def another_member(db, team):
    user = User.objects.create_user(
        username="another_member",
        email="another@test.com",
        password="StrongPassword123!"
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.MEMBER,
        team=team
    )
    return user


@pytest.fixture
def other_team_member(db, other_team):
    user = User.objects.create_user(
        username="other_team_member",
        email="otherteam@test.com",
        password="StrongPassword123!"
    )
    UserProfile.objects.create(
        user=user,
        role=UserProfile.Role.MEMBER,
        team=other_team
    )
    return user


@pytest.fixture
def todo(db, member, team):
    return Todo.objects.create(
        user=member,
        team=team,
        title="Workspace test todo",
        description="Testing workspace permissions"
    )


@pytest.fixture
def assigned_todo(todo, another_member):
    todo.assignee = another_member
    todo.assignment_status = Todo.AssignmentStatus.PENDING
    todo.save()
    return todo


# -------------------------------------------------------------------
# User management and RBAC
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_can_list_users(api_client, admin):
    api_client.force_authenticate(user=admin)

    response = api_client.get("/api/users/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_member_cannot_list_users(api_client, member):
    api_client.force_authenticate(user=member)

    response = api_client.get("/api/users/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_cannot_change_own_role(api_client, admin):
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/users/{admin.id}/",
        {"role": "MEMBER"},
        format="json"
    )

    assert response.status_code == 403
    admin.profile.refresh_from_db()
    assert admin.profile.role == UserProfile.Role.ADMIN


@pytest.mark.django_db
def test_member_cannot_change_user_role(
    api_client, member, another_member
):
    api_client.force_authenticate(user=member)

    response = api_client.patch(
        f"/api/users/{another_member.id}/",
        {"role": "ADMIN"},
        format="json"
    )

    assert response.status_code == 403

    another_member.profile.refresh_from_db()
    assert another_member.profile.role == UserProfile.Role.MEMBER


@pytest.mark.django_db
def test_admin_can_change_another_users_role(
    api_client, admin, another_member
):
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/users/{another_member.id}/",
        {"role": "ADMIN"},
        format="json"
    )

    assert response.status_code == 200

    another_member.profile.refresh_from_db()
    assert another_member.profile.role == UserProfile.Role.ADMIN


@pytest.mark.django_db
def test_admin_can_change_user_team(
    api_client, admin, another_member, other_team
):
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/users/{another_member.id}/",
        {"team": other_team.id},
        format="json"
    )

    assert response.status_code == 200

    another_member.profile.refresh_from_db()
    assert another_member.profile.team == other_team


# -------------------------------------------------------------------
# Teams
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_authenticated_user_can_list_teams(api_client, member):
    api_client.force_authenticate(user=member)

    response = api_client.get("/api/teams/")

    assert response.status_code == 200
    assert isinstance(response.data, list)


@pytest.mark.django_db
def test_unauthenticated_user_cannot_list_teams(api_client):
    response = api_client.get("/api/teams/")

    assert response.status_code == 401


# -------------------------------------------------------------------
# Todo permissions
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_creator_can_retrieve_own_todo(api_client, member, todo):
    api_client.force_authenticate(user=member)

    response = api_client.get(f"/api/todos/{todo.id}/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_unrelated_user_cannot_retrieve_todo(
    api_client, another_member, todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.get(f"/api/todos/{todo.id}/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_creator_cannot_edit_todo_after_assignment(
    api_client, member, assigned_todo
):
    api_client.force_authenticate(user=member)

    response = api_client.patch(
        f"/api/todos/{assigned_todo.id}/",
        {"title": "Changed by creator"},
        format="json"
    )

    assert response.status_code == 403

    assigned_todo.refresh_from_db()
    assert assigned_todo.title == "Workspace test todo"


@pytest.mark.django_db
def test_assignee_can_edit_assigned_todo(
    api_client, another_member, assigned_todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.patch(
        f"/api/todos/{assigned_todo.id}/",
        {"title": "Changed by assignee"},
        format="json"
    )

    assert response.status_code == 200

    assigned_todo.refresh_from_db()
    assert assigned_todo.title == "Changed by assignee"


@pytest.mark.django_db
def test_assigned_todo_cannot_be_deleted_by_creator(
    api_client, member, assigned_todo
):
    api_client.force_authenticate(user=member)

    response = api_client.delete(
        f"/api/todos/{assigned_todo.id}/"
    )

    assert response.status_code == 403
    assert Todo.objects.filter(id=assigned_todo.id).exists()


# -------------------------------------------------------------------
# Todo assignment
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_creator_can_assign_todo_to_teammate(
    api_client, member, another_member, todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": another_member.id},
        format="json"
    )

    assert response.status_code == 200

    todo.refresh_from_db()
    assert todo.assignee == another_member
    assert todo.assignment_status == Todo.AssignmentStatus.PENDING


@pytest.mark.django_db
def test_assignment_creates_notification(
    api_client, member, another_member, todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": another_member.id},
        format="json"
    )

    assert response.status_code == 200

    assert Notification.objects.filter(
        recipient=another_member,
        actor=member,
        todo=todo
    ).exists()


@pytest.mark.django_db
def test_non_creator_cannot_assign_todo(
    api_client, another_member, member, todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": member.id},
        format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_creator_cannot_assign_todo_to_self(
    api_client, member, todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": member.id},
        format="json"
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_assign_todo_to_different_team_member(
    api_client, member, other_team_member, todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": other_team_member.id},
        format="json"
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_assign_todo_twice(
    api_client, member, another_member, assigned_todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{assigned_todo.id}/assign/",
        {"assignee": another_member.id},
        format="json"
    )

    assert response.status_code == 409


# -------------------------------------------------------------------
# Assignment responses
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_assignee_can_accept_assignment(
    api_client, another_member, assigned_todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "ACCEPTED"},
        format="json"
    )

    assert response.status_code == 200

    assigned_todo.refresh_from_db()
    assert assigned_todo.assignment_status == Todo.AssignmentStatus.ACCEPTED


@pytest.mark.django_db
def test_assignee_can_reject_assignment(
    api_client, another_member, assigned_todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "REJECTED"},
        format="json"
    )

    assert response.status_code == 200

    assigned_todo.refresh_from_db()
    assert assigned_todo.assignment_status == Todo.AssignmentStatus.REJECTED


@pytest.mark.django_db
def test_creator_cannot_respond_to_assignment(
    api_client, member, assigned_todo
):
    api_client.force_authenticate(user=member)

    response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "ACCEPTED"},
        format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_cannot_respond_twice_to_assignment(
    api_client, another_member, assigned_todo
):
    api_client.force_authenticate(user=another_member)

    first_response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "ACCEPTED"},
        format="json"
    )

    second_response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "REJECTED"},
        format="json"
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409


@pytest.mark.django_db
def test_assignment_response_notifies_creator(
    api_client, another_member, assigned_todo
):
    api_client.force_authenticate(user=another_member)

    response = api_client.post(
        f"/api/todos/{assigned_todo.id}/respond/",
        {"decision": "ACCEPTED"},
        format="json"
    )

    assert response.status_code == 200

    assert Notification.objects.filter(
        recipient=assigned_todo.user,
        actor=another_member,
        todo=assigned_todo
    ).exists()


# -------------------------------------------------------------------
# Notifications
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_user_can_list_own_notifications(
    api_client, another_member, assigned_todo, member
):
    notification = Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Test notification"
    )

    api_client.force_authenticate(user=another_member)

    response = api_client.get("/api/notifications/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["id"] == notification.id


@pytest.mark.django_db
def test_user_cannot_see_other_users_notifications(
    api_client, member, another_member, assigned_todo
):
    Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Private notification"
    )

    api_client.force_authenticate(user=member)

    response = api_client.get("/api/notifications/")

    assert response.status_code == 200
    assert len(response.data) == 0


@pytest.mark.django_db
def test_user_can_get_unread_notification_count(
    api_client, another_member, member, assigned_todo
):
    Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Unread one"
    )
    Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Unread two"
    )

    api_client.force_authenticate(user=another_member)

    response = api_client.get("/api/notifications/unread-count/")

    assert response.status_code == 200
    assert response.data["unread_count"] == 2


@pytest.mark.django_db
def test_user_can_mark_own_notification_as_read(
    api_client, another_member, member, assigned_todo
):
    notification = Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Test notification"
    )

    api_client.force_authenticate(user=another_member)

    response = api_client.patch(
        f"/api/notifications/{notification.id}/read/",
        format="json"
    )

    assert response.status_code == 200

    notification.refresh_from_db()
    assert notification.is_read is True


@pytest.mark.django_db
def test_user_cannot_mark_another_users_notification_as_read(
    api_client, member, another_member, assigned_todo
):
    notification = Notification.objects.create(
        recipient=another_member,
        actor=member,
        todo=assigned_todo,
        message="Private notification"
    )

    api_client.force_authenticate(user=member)

    response = api_client.patch(
        f"/api/notifications/{notification.id}/read/",
        format="json"
    )

    assert response.status_code == 404

    notification.refresh_from_db()
    assert notification.is_read is False


@pytest.mark.django_db
def test_user_can_mark_all_notifications_as_read(
    api_client, another_member, member, assigned_todo
):
    for index in range(3):
        Notification.objects.create(
            recipient=another_member,
            actor=member,
            todo=assigned_todo,
            message=f"Notification {index}"
        )

    api_client.force_authenticate(user=another_member)

    response = api_client.post("/api/notifications/read-all/")

    assert response.status_code == 200

    assert Notification.objects.filter(
        recipient=another_member,
        is_read=False
    ).count() == 0


# -------------------------------------------------------------------
# Bonus admin dashboard and read-only inspection
# -------------------------------------------------------------------

@pytest.mark.django_db
def test_admin_can_view_dashboard(api_client, admin, todo, assigned_todo):
    api_client.force_authenticate(user=admin)

    response = api_client.get("/api/admin/dashboard/")

    assert response.status_code == 200
    assert response.data["overview"]["total_users"] >= 3
    assert response.data["overview"]["total_todos"] == 1
    assert "completion_rate" in response.data["overview"]
    assert len(response.data["users"]) >= 3
    assert len(response.data["teams"]) >= 1


@pytest.mark.django_db
def test_member_cannot_view_admin_dashboard(api_client, member):
    api_client.force_authenticate(user=member)

    response = api_client.get("/api/admin/dashboard/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_inspect_user_todos_read_only(
    api_client, admin, member, todo, assigned_todo
):
    api_client.force_authenticate(user=admin)

    response = api_client.get(f"/api/admin/users/{member.id}/todos/")

    assert response.status_code == 200
    assert response.data["count"] == 1
    assert {item["id"] for item in response.data["results"]} == {
        todo.id
    }


@pytest.mark.django_db
def test_member_cannot_inspect_another_users_todos(
    api_client, member, another_member
):
    api_client.force_authenticate(user=member)

    response = api_client.get(f"/api/admin/users/{another_member.id}/todos/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_can_view_any_todo_detail_read_only(api_client, admin, todo):
    api_client.force_authenticate(user=admin)

    response = api_client.get(f"/api/todos/{todo.id}/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_cannot_edit_todo(api_client, admin, todo):
    api_client.force_authenticate(user=admin)

    response = api_client.patch(
        f"/api/todos/{todo.id}/",
        {"title": "Admin edited this"},
        format="json",
    )

    assert response.status_code == 403
    todo.refresh_from_db()
    assert todo.title == "Workspace test todo"


@pytest.mark.django_db
def test_admin_cannot_create_todo(api_client, admin):
    api_client.force_authenticate(user=admin)

    response = api_client.post(
        "/api/todos/",
        {"title": "Admin-created task", "description": ""},
        format="json",
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_admin_cannot_assign_or_respond(api_client, admin, todo):
    api_client.force_authenticate(user=admin)

    assign_response = api_client.post(
        f"/api/todos/{todo.id}/assign/",
        {"assignee": admin.id},
        format="json",
    )
    respond_response = api_client.post(
        f"/api/todos/{todo.id}/respond/",
        {"decision": "ACCEPTED"},
        format="json",
    )

    assert assign_response.status_code == 403
    assert respond_response.status_code == 403


@pytest.mark.django_db
def test_admin_cannot_delete_todo(api_client, admin, todo):
    api_client.force_authenticate(user=admin)

    response = api_client.delete(f"/api/todos/{todo.id}/")

    assert response.status_code == 403
    assert Todo.objects.filter(id=todo.id).exists()
