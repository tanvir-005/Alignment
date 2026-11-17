"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

export default function AdminPage() {
  const [users, setUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [currentUser, setCurrentUser] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [accessDenied, setAccessDenied] = useState(false);
  const [selectedUser, setSelectedUser] = useState(null);
  const [userTodos, setUserTodos] = useState([]);
  const [userTodosLoading, setUserTodosLoading] = useState(false);
  const [userTodosError, setUserTodosError] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");
    setAccessDenied(false);

    try {
      const meResponse = await fetch("/api/auth/me", { cache: "no-store" });
      const meData = await meResponse.json();

      if (!meResponse.ok) {
        throw new Error("Unable to identify the current user.");
      }

      setCurrentUser(meData);

      if (meData.role !== "ADMIN") {
        setAccessDenied(true);
        return;
      }

      const [usersResponse, teamsResponse, dashboardResponse] = await Promise.all([
        fetch("/api/users/", { cache: "no-store" }),
        fetch("/api/teams/", { cache: "no-store" }),
        fetch("/api/admin/dashboard/", { cache: "no-store" }),
      ]);

      const [usersData, teamsData, dashboardData] = await Promise.all([
        usersResponse.json(),
        teamsResponse.json(),
        dashboardResponse.json(),
      ]);

      if (!usersResponse.ok) {
        throw new Error(usersData.detail || usersData.error || "Unable to load users.");
      }
      if (!teamsResponse.ok) {
        throw new Error(teamsData.detail || teamsData.error || "Unable to load teams.");
      }
      if (!dashboardResponse.ok) {
        throw new Error(dashboardData.detail || dashboardData.error || "Unable to load dashboard.");
      }

      const userList = Array.isArray(usersData) ? usersData : usersData.results || [];
      const teamList = Array.isArray(teamsData) ? teamsData : teamsData.results || [];

      setUsers(userList);
      setTeams(teamList);
      setDashboard(dashboardData);

      const initialDrafts = {};
      userList.forEach((user) => {
        initialDrafts[user.id] = {
          role: user.role,
          team: user.team?.id ?? user.team ?? "",
        };
      });
      setDrafts(initialDrafts);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function updateDraft(userId, field, value) {
    setDrafts((previous) => ({
      ...previous,
      [userId]: { ...previous[userId], [field]: value },
    }));
  }

  async function saveUser(user) {
    const draft = drafts[user.id];
    if (!draft) return;

    setSavingId(user.id);
    setError("");
    setSuccess("");

    const payload = {
      team: draft.team === "" ? null : Number(draft.team),
    };
    if (user.id !== currentUser?.id) payload.role = draft.role;

    try {
      const response = await fetch(`/api/users/${user.id}/`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await response.json();

      if (!response.ok) {
        const detail = data.detail ||
          (typeof data === "object" ? Object.values(data).flat().join(" ") : null) ||
          data.error || "Unable to update user.";
        throw new Error(detail);
      }

      setSuccess(`Updated ${user.username}.`);
      await loadData();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSavingId(null);
    }
  }

  async function inspectUser(user) {
    setSelectedUser(user);
    setUserTodos([]);
    setUserTodosError("");
    setUserTodosLoading(true);

    try {
      const response = await fetch(`/api/admin/users/${user.id}/todos/`, {
        cache: "no-store",
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.error || "Unable to load user tasks.");
      }
      setUserTodos(data.results || []);
    } catch (err) {
      setUserTodosError(err.message || "Unable to load user tasks.");
    } finally {
      setUserTodosLoading(false);
    }
  }

  const filteredUsers = users.filter((user) => {
    const query = search.toLowerCase();
    return [user.username, user.email, user.first_name, user.last_name]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query));
  });

  if (loading) {
    return <div className={styles.state}>Loading administration...</div>;
  }

  if (accessDenied) {
    return (
      <section className={styles.page}>
        <div className={styles.state}>
          <h1>Access denied</h1>
          <p>You do not have permission to access administration.</p>
        </div>
      </section>
    );
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>WORKSPACE / MANAGEMENT</p>
          <h1>Administration</h1>
          <p className={styles.subtitle}>Workspace overview and user management.</p>
        </div>
        <span className={styles.userCount}>{users.length} users</span>
      </header>

      {error && (
        <div className={styles.errorPanel}>
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}
      {success && <p className={styles.success}>{success}</p>}

      {dashboard && (
        <div className={styles.dashboard}>
          <div className={styles.sectionHeading}>
            <div>
              <p className={styles.eyebrow}>WORKSPACE / OVERVIEW</p>
              <h2>Workspace activity</h2>
            </div>
            <span>Live workspace totals</span>
          </div>

          <div className={styles.metricsGrid}>
            {[
              ["Users", dashboard.overview.total_users],
              ["Teams", dashboard.overview.total_teams],
              ["All todos", dashboard.overview.total_todos],
              ["Incomplete", dashboard.overview.incomplete_todos],
              ["Completed", dashboard.overview.completed_todos],
              ["Pending assignments", dashboard.overview.pending_assignments],
            ].map(([label, value]) => (
              <article className={styles.metricCard} key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>

          <div className={styles.dashboardGrid}>
            <section className={styles.panel}>
              <div className={styles.panelHeading}>
                <h3>Task status</h3>
                <strong>{dashboard.overview.completion_rate}% complete</strong>
              </div>
              {[
                ["Pending", dashboard.task_status.pending, "#b7a27a"],
                ["In progress", dashboard.task_status.in_progress, "#8b9876"],
                ["Completed", dashboard.task_status.completed, "#77785b"],
              ].map(([label, value, color]) => {
                const total = dashboard.overview.total_todos || 1;
                return (
                  <div className={styles.barRow} key={label}>
                    <div className={styles.barLabel}>
                      <span>{label}</span><strong>{value}</strong>
                    </div>
                    <div className={styles.barTrack}>
                      <span style={{ width: `${(value / total) * 100}%`, background: color }} />
                    </div>
                  </div>
                );
              })}
            </section>

            <section className={styles.panel}>
              <div className={styles.panelHeading}>
                <h3>Team overview</h3>
                <span>{dashboard.teams.length} teams</span>
              </div>
              {dashboard.teams.length ? dashboard.teams.map((team) => (
                <div className={styles.teamRow} key={team.id}>
                  <div>
                    <strong>{team.name}</strong>
                    <span>{team.members} members · {team.todos} todos</span>
                  </div>
                  <div className={styles.teamProgress}>
                    <strong>{team.completion_rate}%</strong>
                    <span>{team.completed_todos}/{team.todos} completed</span>
                  </div>
                </div>
              )) : <p className={styles.muted}>No teams available.</p>}
            </section>
          </div>

          <section className={styles.panel}>
            <div className={styles.panelHeading}>
              <h3>User activity</h3>
              <span>Select a user to inspect their todos</span>
            </div>
            <div className={styles.activityTableWrap}>
              <table className={styles.activityTable}>
                <thead>
                  <tr>
                    <th>User</th><th>Team</th><th>Assigned</th><th>Completed</th>
                    <th>Pending</th><th>Completion</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {dashboard.users.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <strong>{item.first_name || item.username}</strong>
                        <small>@{item.username}</small>
                      </td>
                      <td>{item.team || "—"}</td>
                      <td>{item.assigned_todos}</td>
                      <td>{item.completed_todos}</td>
                      <td>{item.pending_todos}</td>
                      <td>
                        <div className={styles.rateCell}>
                          <span>{item.completion_rate}%</span>
                          <div className={styles.miniTrack}>
                            <i style={{ width: `${item.completion_rate}%` }} />
                          </div>
                        </div>
                      </td>
                      <td>
                        <button
                          className={styles.textButton}
                          onClick={() => inspectUser(users.find((user) => user.id === item.id) || item)}
                        >
                          Inspect
                        </button>
                      </td>
                    </tr>
                  ))}
                  {!dashboard.users.length && (
                    <tr><td colSpan={7} className={styles.empty}>No users available.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className={styles.panel}>
            <div className={styles.panelHeading}>
              <h3>Recent activity</h3>
              <span>Latest assignment events</span>
            </div>
            {dashboard.recent_activity.length ? (
              <div className={styles.recentList}>
                {dashboard.recent_activity.map((item) => (
                  <Link className={styles.recentItem} href={`/todos/${item.todo_id}`} key={item.id}>
                    <span>{item.message}</span>
                    <time>{new Date(item.created_at).toLocaleString()}</time>
                  </Link>
                ))}
              </div>
            ) : <p className={styles.muted}>No activity has been recorded yet.</p>}
          </section>
        </div>
      )}

      {selectedUser && (
        <div className={styles.modalBackdrop} role="presentation" onClick={() => setSelectedUser(null)}>
          <section
            className={styles.userDrawer}
            role="dialog"
            aria-modal="true"
            aria-labelledby="user-todos-title"
            onClick={(event) => event.stopPropagation()}
          >
            <div className={styles.panelHeading}>
              <div>
                <p className={styles.eyebrow}>USER / READ ONLY</p>
                <h2 id="user-todos-title">{selectedUser.first_name || selectedUser.username}</h2>
                <span>
                  @{selectedUser.username} · {selectedUser.role} · {selectedUser.team?.name || selectedUser.team || "No team"}
                </span>
              </div>
              <button className={styles.closeButton} onClick={() => setSelectedUser(null)} aria-label="Close user tasks">×</button>
            </div>
            {userTodosLoading ? (
              <p className={styles.muted}>Loading user todos...</p>
            ) : userTodosError ? (
              <p className={styles.errorText}>{userTodosError}</p>
            ) : userTodos.length ? (
              <div className={styles.userTodoList}>
                {userTodos.map((todo) => (
                  <Link href={`/todos/${todo.id}`} key={todo.id} className={styles.userTodo}>
                    <strong>{todo.title}</strong>
                    <span>
                      {todo.task_status.replaceAll("_", " ").toLowerCase()} · Creator: {todo.creator} · Assignee: {todo.assignee || "Unassigned"}
                    </span>
                    <small>{todo.team || "No team"} · Updated {new Date(todo.updated_at).toLocaleDateString()}</small>
                  </Link>
                ))}
              </div>
            ) : <p className={styles.muted}>This user has no todos.</p>}
            <p className={styles.readOnlyNote}>
              Administrator inspection is read-only. Task changes must be made by permitted task participants.
            </p>
          </section>
        </div>
      )}

      <div className={styles.toolbar}>
        <input
          type="search"
          placeholder="Search users..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
          aria-label="Search users"
        />
        <span>{filteredUsers.length} results</span>
      </div>

      <div className={styles.tableWrapper}>
        <table className={styles.table}>
          <thead>
            <tr>
              <th>User</th><th>Email</th><th>Role</th><th>Team</th>
              <th>Created</th><th>Assigned</th><th></th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((user) => {
              const isCurrentUser = user.id === currentUser?.id;
              const draft = drafts[user.id] || {};
              return (
                <tr key={user.id}>
                  <td>
                    <div className={styles.userInfo}>
                      <strong>{[user.first_name, user.last_name].filter(Boolean).join(" ") || user.username}</strong>
                      <span>@{user.username}</span>
                      {isCurrentUser && <small>YOU</small>}
                    </div>
                  </td>
                  <td className={styles.email}>{user.email}</td>
                  <td>
                    <select
                      value={draft.role || user.role}
                      disabled={isCurrentUser}
                      onChange={(event) => updateDraft(user.id, "role", event.target.value)}
                      aria-label={`Role for ${user.username}`}
                    >
                      <option value="MEMBER">Member</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </td>
                  <td>
                    <select
                      value={draft.team ?? ""}
                      onChange={(event) => updateDraft(user.id, "team", event.target.value)}
                      aria-label={`Team for ${user.username}`}
                    >
                      <option value="">No team</option>
                      {teams.map((team) => <option key={team.id} value={team.id}>{team.name}</option>)}
                    </select>
                  </td>
                  <td className={styles.todoCount}>{user.created_todo_count ?? 0}</td>
                  <td className={styles.todoCount}>{user.assigned_todo_count ?? 0}</td>
                  <td>
                    <button className={styles.saveButton} disabled={savingId === user.id} onClick={() => saveUser(user)}>
                      {savingId === user.id ? "Saving..." : "Save"}
                    </button>
                  </td>
                </tr>
              );
            })}
            {filteredUsers.length === 0 && (
              <tr><td colSpan={7} className={styles.empty}>No users found.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
