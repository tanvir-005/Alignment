# Teamboard

Team task management for an organisation. An **admin** (the owner) creates teams and
decides who is in them, each team has exactly one **project manager (PM)**, PMs assign work,
and **assignees** move it forward on a Kanban board.

Stack (unchanged): Django 5 + DRF + SimpleJWT + drf-spectacular + SQLite · Next.js 15 (App Router, JS, CSS Modules) · pytest.

## Roles and rules

| Who | Can | Cannot |
|---|---|---|
| **Admin** | Create/edit/delete teams, choose a team's PM on creation, add/remove members, replace a PM, deactivate people. Sees every team and task. | Create or change tasks. Belong to a team. |
| **PM** (per team) | Create, edit, delete and assign tasks of *their* team to some or all members (themselves included). Change task status. | Add/remove members. |
| **Assignee** | Change the status of tasks assigned to them. | Edit or delete tasks. |
| **Member** | See all tasks of teams they belong to (read-only unless assigned). | |

- Everyone who signs up is a plain user with **no team**; they see a "waiting for an admin" screen until added.
- PM is a role *inside a team*. A user can be PM of several teams and a plain member of others.
- No team without a PM (a team is created together with its PM) and no PM without a team (PM-ness lives on the membership).
  A PM cannot be removed directly; use **Replace PM**, which swaps atomically.
- Joining, leaving, adding and removing are admin-only. Removing someone from a team unassigns them from that
  team's tasks, and **deletes every task they were the last assignee of** (the admin sees an exact count before confirming).
- A task needs at least one assignee, and assignees must be members of the task's team.
- Status is shared per task (Pending / In progress / Completed): any assignee or the PM can change it; the activity log records who did.
- **My tasks** shows a Kanban board with only the tasks you can change (assigned to you, or in teams you manage),
  and a list of the other tasks in your teams. Each team page has the same split, per team.

## Run it

```bash
# backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_demo            # optional demo organisation
python manage.py runserver 8080

# frontend (second terminal)
cd frontend
cp .env.example .env.local
npm install
npm run dev                           # http://localhost:3000
```

Create the owner account (the first admin cannot sign up through the UI):

```bash
python manage.py createadmin --email owner@yourorg.com --name "Olivia Owner"
```

Demo data (`seed_demo`): admin `admin@example.com` / `Admin@2026Demo`; users `priya@`, `omar@`, `lena@`,
`jonas@`, `mei@`, `ana@`, `tomas@`, `sam@example.com` / `Demo@2026Pass`.
Priya is PM of Atlas and member of Beacon; Omar is the reverse; Sam has no team yet.

Tests: `pytest` (84 tests covering the permission matrix, PM replacement, member-removal cascade, visibility, emails and the digest).
API docs: `python manage.py spectacular --file schema.yml` (committed as `schema.yml`) or `/api/schema/` if enabled.


## Emails and the daily digest

| Event | Who is emailed |
|---|---|
| A task is assigned (on creation, or added later by the PM) | Each newly assigned person, never the person who assigned them |
| A task's status changes | That team's PM, never when the PM made the change themselves |
| 10 PM every day | Each PM, one summary per team they manage, covering the previous 24 hours |

Emails go out only after the change is saved, and a mail failure never breaks the app (it is logged).
By default emails are **printed in the backend terminal** (demo mode). To send real mail, set
`EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` and the `EMAIL_*` values in `.env`
(see `.env.example`). `FRONTEND_URL` controls the links inside emails and `TIME_ZONE` decides what "10 PM" means.

**The digest** is a command; the schedule lives outside the app so it survives restarts and works anywhere:

```bash
python manage.py send_daily_digest              # what the scheduler runs
python manage.py send_daily_digest --dry-run    # print instead of sending
python manage.py send_daily_digest --force      # send again even if already sent today
python manage.py send_daily_digest --hours 72   # custom window (testing)
python manage.py send_daily_digest --team 3     # one team only
```

It skips teams with no activity, and records one `DigestLog` row per team per day so a re-run never double-sends.
Deleted tasks are included (a small tombstone is kept for that purpose).

Schedule it for 22:00 (server time, set `TIME_ZONE`):

- **Linux/macOS (cron):** `crontab -e` and add
  `0 22 * * * cd /path/to/todo-workspace && .venv/bin/python manage.py send_daily_digest >> digest.log 2>&1`
- **Windows:** Task Scheduler, daily at 22:00, action `C:\path\.venv\Scripts\python.exe manage.py send_daily_digest`, start in the project folder.
- **Docker Compose:** `docker compose up scheduler` runs a small loop that triggers it at 22:00 container time (`TZ` in the compose file).

## Structure

```
todos/
  models.py            Team, TeamMembership (PM/MEMBER), Todo, TodoAssignment, Notification, TodoActivity
  permissions.py       single source of truth for who can do what
  selectors.py         scoped querysets (visible / actionable)
  services/            team_service, todo_service (atomic business rules), notifications, activity
  views.py, urls.py    thin API layer
  tests/               pytest suite
frontend/src/
  app/(auth)           login, register
  app/(workspace)      my-tasks, teams/[id], todos/[id], notifications, admin/*
  app/api/[...path]    one authenticated pass-through to Django (cookies hold the JWTs)
  components/          layout shell, ui primitives, kanban, todo list/form, admin modals
```

## API summary

`/api/auth/{register,login,refresh,me}` · `/api/teams/` (+ `members/`, `members/<id>/impact/`, `replace-pm/`) ·
`/api/users/` (admin) · `/api/todos/?scope=actionable|mine|other|all&team=&status=&priority=&search=&ordering=` ·
`/api/todos/<id>/{status,activities}/` · `/api/notifications/…` · `/api/admin/overview/`.
Every todo carries `can_change_status`, `can_edit` and `is_assignee` so the UI never re-derives permissions.
