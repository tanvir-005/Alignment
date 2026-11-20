# The Scroll of Procrastination

A team-based TODO management system built with Django REST Framework and Next.js.

## Overview

The Scroll of Procrastination is a collaborative task management application where team members can create, assign, track, and manage tasks. It includes role-based access control, assignment workflows, notifications, a Kanban board, and an administrative dashboard.

## Features

- **Authentication:** JWT-based authentication using HttpOnly cookies.
- **Role management:** Admin and Member roles with role-based permissions.
- **Team management:** Organize users into teams.
- **Task management:** Create, view, update, search, filter, sort, and paginate tasks.
- **Task assignment:** Assign tasks to teammates within the same team.
- **Assignment workflow:** Assignees can accept or reject task assignments.
- **Task status management:** Move tasks between Pending, In Progress, and Completed states.
- **Kanban board:** Visualize tasks in three status columns and move them using directional arrow controls.
- **Notifications:** Receive updates about task assignments and responses.
- **Admin dashboard:** View system statistics, user activity, team information, and recent activity.
- **User task inspection:** Administrators can inspect individual users' tasks through the dashboard.
- **Custom error page:** Dedicated not-found page for unavailable routes.

## Technology Stack

| Layer | Technologies |
|---|---|
| Backend | Python, Django, Django REST Framework |
| Authentication | Simple JWT, HttpOnly cookies |
| API documentation | drf-spectacular |
| Database | SQLite |
| Frontend | Next.js, React, JavaScript |
| Styling | CSS Modules |
| Testing | pytest, pytest-django |

## Architecture

The application uses a Backend-for-Frontend (BFF) architecture.

```text
Browser
   |
   v
Next.js Frontend
   |
   v
Next.js API Routes
   |
   v
Django REST API
   |
   v
SQLite Database
```

JWT tokens are stored in HttpOnly cookies. The browser communicates with Next.js API routes, which handle requests to the Django backend. Authentication credentials are not exposed to browser-side JavaScript.

## Business Rules

### Roles

- **ADMIN:** Can manage users, roles, and team assignments. Has read-only access to task information.
- **MEMBER:** Can create and manage their own tasks and interact with tasks assigned to them.

The first registered user becomes an admin. Subsequent registrations receive the Member role.

### Tasks

Task statuses:

- `PENDING`
- `IN_PROGRESS`
- `COMPLETED`

Status transitions follow this sequence:

```text
PENDING <-> IN_PROGRESS <-> COMPLETED
```

Tasks can only move one stage at a time. Skipping stages is not allowed.

### Assignments

Assignment statuses:

- `PENDING`
- `ACCEPTED`
- `REJECTED`

Key permissions:

- A task can be assigned to a teammate in the same team.
- Users cannot assign tasks to themselves.
- Assignees can accept or reject assignments.
- After assignment, only the assignee can edit the task.
- The creator can view the task but cannot edit it after assignment.
- Assigned tasks cannot be deleted.
- An assignee must accept an assignment before changing its task status.
- Only the assigned user can update an accepted assigned task.
- For unassigned tasks, only the creator can change the task status.
- Administrators have read-only access to tasks and cannot create, edit, assign, change the status of, or delete them.

## Application Pages

### My Tasks

The primary task management interface. Members can create tasks, search and filter existing tasks, sort results, navigate paginated results, and manage assignment workflows.

### Kanban

A separate visual task management interface with three columns:

- Pending
- In Progress
- Completed

Each task card has left and right arrow controls to move it between adjacent statuses. Controls are enabled or disabled according to the task's current status and the user's permissions. The board does not use drag-and-drop.

### Administration

The administrative dashboard provides an overview of the workspace, including task statistics, status distribution, team information, user activity, and recent activity.

Administrators can inspect individual users' tasks without modifying them.

## Project Structure

```text
todo-workspace/
├── config/                 # Django project configuration
├── todos/                  # Tasks, users, teams, notifications
├── frontend/               # Next.js application
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── manage.py
├── pytest.ini
├── requirements.txt
└── README.md
```

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 24+
- npm

### 1. Clone the repository

```bash
git clone https://github.com/tanvir-005/todo-workspace.git
cd todo-workspace
```

### 2. Set up the backend

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables:

```bash
cp .env.example .env
```

Update the environment values as needed, including the Django secret key and allowed hosts.

Run migrations and load demo data:

```bash
python manage.py migrate
python manage.py seed_demo
```

Start the backend:

```bash
python manage.py runserver 8080
```

Backend API: `http://127.0.0.1:8080/api/`

### 3. Set up the frontend

Open another terminal:

```bash
cd frontend
npm install
```

Create `frontend/.env.local`:

```env
DJANGO_API_URL=http://127.0.0.1:8080/api
```

Start the frontend:

```bash
npm run dev
```

Frontend: `http://localhost:3000`

## Demo Accounts

The following accounts are created by `seed_demo` on a fresh database.

| Username | Password | Role | Team |
|---|---|---|---|
| `demo_admin` | `Admin@2026Demo` | ADMIN | Team Alpha |
| `alice` | `Alice@2026Secure` | MEMBER | Team Alpha |
| `bob` | `Bob@2026Secure` | MEMBER | Team Alpha |
| `charlie` | `Charlie@2026Secure` | MEMBER | Team Beta |

The seed command is repeatable and does not overwrite existing users' passwords, roles, or team assignments.

## API Overview

All backend endpoints are prefixed with `/api/`.

| Resource | Endpoint |
|---|---|
| Authentication | `/auth/` |
| Tasks | `/todos/` |
| Task status updates | `/todos/{id}/status/` |
| Assignments | `/assignments/` |
| Notifications | `/notifications/` |
| Teams | `/teams/` |
| Users | `/users/` |
| Admin dashboard | `/admin/dashboard/` |
| Admin user task inspection | `/admin/users/{id}/todos/` |

API documentation is available through the configured API documentation endpoint.

## Testing

Run the backend test suite from the project root:

```bash
pytest -v
```

The test suite covers authentication, task operations, permissions, assignments, notifications, filtering, sorting, pagination, and task status transitions.

## Useful Commands

**Backend**

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver 8080
pytest -v
```

**Frontend**

```bash
npm run dev
npm run lint
npm run build
npm start
```