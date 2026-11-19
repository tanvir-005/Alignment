"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const COLUMNS = [
  {
    value: "PENDING",
    label: "Pending",
    description: "Tasks waiting to be started",
  },
  {
    value: "IN_PROGRESS",
    label: "In progress",
    description: "Tasks currently being worked on",
  },
  {
    value: "COMPLETED",
    label: "Completed",
    description: "Finished tasks",
  },
];

const STATUS_TRANSITIONS = {
  PENDING: {
    previous: null,
    next: "IN_PROGRESS",
  },
  IN_PROGRESS: {
    previous: "PENDING",
    next: "COMPLETED",
  },
  COMPLETED: {
    previous: "IN_PROGRESS",
    next: null,
  },
};

function formatDate(value) {
  if (!value) return "—";

  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

function formatStatus(value) {
  return value?.replaceAll("_", " ").toLowerCase() || "unknown";
}

export default function KanbanPage() {
  const [todos, setTodos] = useState([]);
  const [user, setUser] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [movingIds, setMovingIds] = useState([]);

  const loadTodos = useCallback(async (showRefresh = false) => {
    if (showRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError("");

    try {
      const allTodos = [];
      let page = 1;
      let hasNext = true;

      while (hasNext) {
        const params = new URLSearchParams({
          limit: "50",
          page: String(page),
          sort_by: "created_at",
          order: "desc",
        });

        const response = await fetch(`/api/todos/?${params.toString()}`, {
          cache: "no-store",
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail || data.error || "Unable to load tasks."
          );
        }

        if (Array.isArray(data)) {
          allTodos.push(...data);
          hasNext = false;
        } else {
          allTodos.push(...(data.results || []));
          hasNext = Boolean(data.next);
          page += 1;
        }

        if (page > 100) {
          throw new Error(
            "Too many tasks to load. Please contact the administrator."
          );
        }
      }

      setTodos(allTodos);
    } catch (err) {
      setError(err.message || "Unable to load the Kanban board.");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  const loadUser = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/me", {
        cache: "no-store",
      });

      if (!response.ok) {
        throw new Error("Unable to load your profile.");
      }

      setUser(await response.json());
    } catch (err) {
      console.error("Unable to load current user:", err);
    }
  }, []);

  useEffect(() => {
    loadTodos();
    loadUser();
  }, [loadTodos, loadUser]);

  const groupedTodos = useMemo(() => {
    const groups = {
      PENDING: [],
      IN_PROGRESS: [],
      COMPLETED: [],
    };

    const query = search.trim().toLowerCase();

    todos.forEach((todo) => {
      if (!groups[todo.task_status]) return;

      const matchesSearch =
        !query ||
        todo.title.toLowerCase().includes(query) ||
        (todo.description || "").toLowerCase().includes(query);

      if (matchesSearch) {
        groups[todo.task_status].push(todo);
      }
    });

    return groups;
  }, [todos, search]);

  const canUpdateTodo = useCallback(
    (todo) => {
      if (!user || user.role === "ADMIN") return false;

      // An unassigned todo can be updated by its creator.
      if (todo.assignee === null) {
        return todo.creator === user.id;
      }

      // An assigned todo can only be updated by its accepted assignee.
      return (
        todo.assignee === user.id &&
        todo.assignment_status === "ACCEPTED"
      );
    },
    [user]
  );

  async function moveTodo(todo, direction) {
    const transitions = STATUS_TRANSITIONS[todo.task_status];
    const nextStatus = transitions?.[direction];

    if (!nextStatus || movingIds.includes(todo.id)) return;

    if (!canUpdateTodo(todo)) {
      setNotice("You do not have permission to update this task.");
      return;
    }

    setMovingIds((current) => [...current, todo.id]);
    setNotice("");

    try {
      const response = await fetch(`/api/todos/${todo.id}/status/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          task_status: nextStatus,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "Unable to change task status."
        );
      }

      setTodos((current) =>
        current.map((item) => (item.id === todo.id ? data : item))
      );

      setNotice(
        `"${todo.title}" moved to ${formatStatus(nextStatus)}.`
      );
    } catch (err) {
      setNotice(err.message || "Unable to update task.");
    } finally {
      setMovingIds((current) =>
        current.filter((id) => id !== todo.id)
      );
    }
  }

  const totalCount = todos.length;
  const visibleCount = Object.values(groupedTodos).reduce(
    (total, items) => total + items.length,
    0
  );

  return (
    <section className={styles.page}>
      <header className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>WORKSPACE / KANBAN</p>
          <h1>Kanban board</h1>
          <p className={styles.subtitle}>
            Track your tasks and move them between stages.
          </p>
        </div>

        <button
          type="button"
          className={styles.refreshButton}
          onClick={() => loadTodos(true)}
          disabled={loading || refreshing}
        >
          {refreshing ? "Refreshing..." : "Refresh"}
        </button>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.searchWrapper}>
          <input
            type="search"
            placeholder="Search tasks..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            aria-label="Search tasks"
          />
        </div>

        <div className={styles.summary}>
          <span>{visibleCount} shown</span>
          <span>{totalCount} total tasks</span>
          {user?.role === "ADMIN" && <span>Read-only view</span>}
        </div>
      </div>

      {notice && (
        <div className={styles.notice} role="status">
          <span>{notice}</span>
          <button
            type="button"
            onClick={() => setNotice("")}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      {error && (
        <div className={styles.errorPanel}>
          <p>{error}</p>
          <button
            type="button"
            onClick={() => loadTodos(true)}
            className={styles.refreshButton}
          >
            Try again
          </button>
        </div>
      )}

      {loading ? (
        <div className={styles.state}>Loading Kanban board...</div>
      ) : !error && totalCount === 0 ? (
        <div className={styles.state}>
          <h2>No tasks yet</h2>
          <p>Create or receive a task to see it on your board.</p>
          <Link href="/todos" className={styles.todosLink}>
            Go to My Tasks
          </Link>
        </div>
      ) : !error && visibleCount === 0 ? (
        <div className={styles.state}>
          <h2>No matching tasks</h2>
          <p>Try a different search term.</p>
        </div>
      ) : (
        <div className={styles.board}>
          {COLUMNS.map((column) => {
            const columnTodos = groupedTodos[column.value];

            return (
              <section className={styles.column} key={column.value}>
                <header className={styles.columnHeader}>
                  <div className={styles.columnHeading}>
                    <span
                      className={`${styles.statusDot} ${
                        styles[`dot${column.value}`]
                      }`}
                    />
                    <h2>{column.label}</h2>
                    <span className={styles.count}>
                      {columnTodos.length}
                    </span>
                  </div>

                  <p>{column.description}</p>
                </header>

                <div className={styles.cardList}>
                  {columnTodos.map((todo) => {
                    const transitions =
                      STATUS_TRANSITIONS[todo.task_status];

                    const canMove = canUpdateTodo(todo);
                    const isMoving = movingIds.includes(todo.id);

                    const leftEnabled =
                      canMove && Boolean(transitions?.previous) && !isMoving;

                    const rightEnabled =
                      canMove && Boolean(transitions?.next) && !isMoving;

                    return (
                      <article className={styles.card} key={todo.id}>
                        <div className={styles.cardTop}>
                          <span className={styles.taskId}>
                            TASK-{todo.id}
                          </span>

                          <span className={styles.assignmentStatus}>
                            {todo.assignee === null
                              ? "Unassigned"
                              : formatStatus(todo.assignment_status)}
                          </span>
                        </div>

                        <Link
                          href={`/todos/${todo.id}`}
                          className={styles.cardTitle}
                        >
                          {todo.title}
                        </Link>

                        {todo.description && (
                          <p className={styles.description}>
                            {todo.description}
                          </p>
                        )}

                        <div className={styles.cardMeta}>
                          <span>
                            {todo.creator === user?.id
                              ? "Created by you"
                              : "Assigned to you"}
                          </span>
                          <time dateTime={todo.created_at}>
                            {formatDate(todo.created_at)}
                          </time>
                        </div>

                        <div className={styles.cardActions}>
                          <button
                            type="button"
                            className={`${styles.arrowButton} ${
                              leftEnabled ? styles.arrowActive : ""
                            }`}
                            disabled={!leftEnabled}
                            onClick={() => moveTodo(todo, "previous")}
                            aria-label={`Move ${todo.title} to previous status`}
                            title={
                              transitions?.previous
                                ? `Move to ${formatStatus(transitions.previous)}`
                                : "Already at the first status"
                            }
                          >
                            ←
                          </button>

                          <span className={styles.currentStatus}>
                            {isMoving
                              ? "Updating..."
                              : formatStatus(todo.task_status)}
                          </span>

                          <button
                            type="button"
                            className={`${styles.arrowButton} ${
                              rightEnabled ? styles.arrowActive : ""
                            }`}
                            disabled={!rightEnabled}
                            onClick={() => moveTodo(todo, "next")}
                            aria-label={`Move ${todo.title} to next status`}
                            title={
                              transitions?.next
                                ? `Move to ${formatStatus(transitions.next)}`
                                : "Already at the last status"
                            }
                          >
                            →
                          </button>
                        </div>

                        {!canMove && (
                          <p className={styles.permissionNote}>
                            {user?.role === "ADMIN"
                              ? "Administrators have read-only access."
                              : todo.assignee !== null &&
                                  todo.assignment_status !== "ACCEPTED"
                                ? "Accept the assignment before changing its status."
                                : "You cannot change this task's status."}
                          </p>
                        )}
                      </article>
                    );
                  })}

                  {columnTodos.length === 0 && (
                    <div className={styles.emptyColumn}>
                      No tasks in this stage.
                    </div>
                  )}
                </div>
              </section>
            );
          })}
        </div>
      )}
    </section>
  );
}