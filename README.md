# The Scroll of Procrastination

A team-based TODO management system built with Django REST Framework and Next.js.

## Overview

The Scroll of Procrastination is a collaborative task management application where team members can create, assign, track, and manage tasks. It includes role-based access control, assignment workflows, and notifications.

## Features

- **Authentication:** JWT-based login and registration.
- **Role management:** Admin and Member roles.
- **Team management:** Organize users into teams.
- **Task management:** Create, view, update, search, filter, sort, and paginate tasks.
- **Task assignment:** Assign tasks to teammates within the same team.
- **Assignment workflow:** Assignees can accept or reject assignments.
- **Notifications:** Receive updates about task assignments and responses.
- **Admin dashboard:** Manage users, roles, and team assignments.

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

JWT tokens are stored in HttpOnly cookies. The browser communicates with Next.js API routes, which handle requests to the Django backend.

## Business Rules

### Roles

- **ADMIN:** Can manage users, roles, and team assignments.
- **MEMBER:** Can manage tasks and interact with assigned tasks.

The first registered user becomes an admin. Subsequent registrations receive the Member role.

### Tasks

Task statuses:

- `PENDING`
- `IN_PROGRESS`
- `COMPLETED`

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
- Assigned tasks cannot be deleted.
- The creator can view the task but cannot edit it after assignment.

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
| Assignments | `/assignments/` |
| Notifications | `/notifications/` |
| Teams | `/teams/` |
| Users | `/users/` |

API documentation is available through the configured API documentation endpoint.

## Testing

Run the backend test suite from the project root:

```bash
pytest -v
```

The test suite covers authentication, task operations, permissions, assignments, notifications, filtering, sorting, and pagination.

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