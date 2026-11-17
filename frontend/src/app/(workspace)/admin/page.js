
"use client";

import { useCallback, useEffect, useState } from "react";
import styles from "./page.module.css";

export default function AdminPage() {
  const [users, setUsers] = useState([]);
  const [teams, setTeams] = useState([]);
  const [currentUser, setCurrentUser] = useState(null);
  const [drafts, setDrafts] = useState({});
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingId, setSavingId] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const loadData = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [usersResponse, teamsResponse, meResponse] =
        await Promise.all([
          fetch("/api/users/", { cache: "no-store" }),
          fetch("/api/teams/", { cache: "no-store" }),
          fetch("/api/auth/me", { cache: "no-store" }),
        ]);

      const [usersData, teamsData, meData] = await Promise.all([
        usersResponse.json(),
        teamsResponse.json(),
        meResponse.json(),
      ]);

      if (!usersResponse.ok) {
        throw new Error(
          usersData.detail || usersData.error || "Unable to load users."
        );
      }

      if (!teamsResponse.ok) {
        throw new Error(
          teamsData.detail || teamsData.error || "Unable to load teams."
        );
      }

      if (!meResponse.ok) {
        throw new Error("Unable to identify the current user.");
      }

      const userList = Array.isArray(usersData)
        ? usersData
        : usersData.results || [];

      const teamList = Array.isArray(teamsData)
        ? teamsData
        : teamsData.results || [];

      setUsers(userList);
      setTeams(teamList);
      setCurrentUser(meData);

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
      [userId]: {
        ...previous[userId],
        [field]: value,
      },
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

    // The backend does not allow users to change their own role.
    if (user.id !== currentUser?.id) {
      payload.role = draft.role;
    }

    try {
      const response = await fetch(`/api/users/${user.id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      const data = await response.json();

      if (!response.ok) {
        const detail =
          data.detail ||
          (typeof data === "object"
            ? Object.values(data).flat().join(" ")
            : null) ||
          data.error ||
          "Unable to update user.";

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

  const filteredUsers = users.filter((user) => {
    const query = search.toLowerCase();

    return [
      user.username,
      user.email,
      user.first_name,
      user.last_name,
    ]
      .filter(Boolean)
      .some((value) => value.toLowerCase().includes(query));
  });

  if (loading) {
    return <div className={styles.state}>Loading administration...</div>;
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>WORKSPACE / MANAGEMENT</p>
          <h1>User management</h1>
          <p className={styles.subtitle}>
            Manage user roles and team memberships.
          </p>
        </div>

        <span className={styles.userCount}>
          {users.length} users
        </span>
      </header>

      {error && (
        <div className={styles.errorPanel}>
          <span>{error}</span>
          <button onClick={loadData}>Retry</button>
        </div>
      )}

      {success && <p className={styles.success}>{success}</p>}

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
              <th>User</th>
              <th>Email</th>
              <th>Role</th>
              <th>Team</th>
              <th></th>
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
                      <strong>
                        {[user.first_name, user.last_name]
                          .filter(Boolean)
                          .join(" ") || user.username}
                      </strong>
                      <span>@{user.username}</span>
                      {isCurrentUser && (
                        <small>YOU</small>
                      )}
                    </div>
                  </td>

                  <td className={styles.email}>{user.email}</td>

                  <td>
                    <select
                      value={draft.role || user.role}
                      disabled={isCurrentUser}
                      onChange={(event) =>
                        updateDraft(user.id, "role", event.target.value)
                      }
                      aria-label={`Role for ${user.username}`}
                    >
                      <option value="MEMBER">Member</option>
                      <option value="ADMIN">Admin</option>
                    </select>
                  </td>

                  <td>
                    <select
                      value={draft.team ?? ""}
                      onChange={(event) =>
                        updateDraft(user.id, "team", event.target.value)
                      }
                      aria-label={`Team for ${user.username}`}
                    >
                      <option value="">No team</option>

                      {teams.map((team) => (
                        <option key={team.id} value={team.id}>
                          {team.name}
                        </option>
                      ))}
                    </select>
                  </td>

                  <td>
                    <button
                      className={styles.saveButton}
                      disabled={savingId === user.id}
                      onClick={() => saveUser(user)}
                    >
                      {savingId === user.id ? "Saving..." : "Save"}
                    </button>
                  </td>
                </tr>
              );
            })}

            {filteredUsers.length === 0 && (
              <tr>
                <td colSpan={5} className={styles.empty}>
                  No users found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
