
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

const STATUS_OPTIONS = [
  { value: "", label: "All tasks" },
  { value: "pending", label: "Pending" },
  { value: "in_progress", label: "In progress" },
  { value: "completed", label: "Completed" },
];

function formatStatus(status) {
  return status?.replaceAll("_", " ").toLowerCase() || "unknown";
}

function formatDate(value) {
  if (!value) return "—";

  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
  }).format(new Date(value));
}

export default function TodosPage() {
  const [todos, setTodos] = useState([]);
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("created_at");
  const [order, setOrder] = useState("desc");
  const [page, setPage] = useState(1);

  const [pagination, setPagination] = useState({
    next: null,
    previous: null,
  });

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [creating, setCreating] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formError, setFormError] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const loadTodos = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams();

      if (status) params.set("status", status);
      if (search.trim()) params.set("search", search.trim());

      params.set("sort", sort);
      params.set("order", order);
      params.set("page", String(page));

      const response = await fetch(`/api/todos/?${params.toString()}`, {
        cache: "no-store",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Unable to load tasks.");
      }

      setTodos(Array.isArray(data) ? data : data.results || []);
      setPagination({
        next: Array.isArray(data) ? null : data.next,
        previous: Array.isArray(data) ? null : data.previous,
      });
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, [status, search, sort, order, page]);

  useEffect(() => {
    loadTodos();
  }, [loadTodos]);

  useEffect(() => {
    async function loadUser() {
      try {
        const response = await fetch("/api/auth/me", {
          cache: "no-store",
        });

        if (response.ok) {
          setUser(await response.json());
        }
      } catch (err) {
        console.error("Unable to load current user:", err);
      }
    }

    loadUser();
  }, []);

  async function handleCreate(event) {
    event.preventDefault();

    if (!title.trim()) {
      setFormError("A task title is required.");
      return;
    }

    setCreating(true);
    setFormError("");

    try {
      const response = await fetch("/api/todos/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || data.error || "Unable to create task.");
      }

      setTitle("");
      setDescription("");
      setShowCreateForm(false);
      setStatus("");
      setSearch("");
      setPage(1);

      await loadTodos();
    } catch (err) {
      setFormError(err.message || "Something went wrong.");
    } finally {
      setCreating(false);
    }
  }

  function changeFilter(value) {
    setStatus(value);
    setPage(1);
  }

  function changeSort(value) {
    setSort(value);
    setPage(1);
  }

  function changeOrder(value) {
    setOrder(value);
    setPage(1);
  }

  return (
    <section className={styles.page}>
      <div className={styles.pageHeader}>
        <div>
          <p className={styles.eyebrow}>WORKSPACE / TASKS</p>
          <h1>My tasks</h1>
          <p className={styles.subtitle}>
            Tasks created by you or assigned to you.
          </p>
        </div>

        <button
          className={styles.primaryButton}
          onClick={() => {
            setShowCreateForm((value) => !value);
            setFormError("");
          }}
        >
          {showCreateForm ? "Cancel" : "+ New task"}
        </button>
      </div>

      {showCreateForm && (
        <form className={styles.createForm} onSubmit={handleCreate}>
          <div className={styles.formHeader}>
            <h2>Create a task</h2>
            <p>New tasks will be added to your team.</p>
          </div>

          <label htmlFor="task-title">Title</label>
          <input
            id="task-title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="What needs to be done?"
            maxLength={255}
            required
          />

          <label htmlFor="task-description">Description</label>
          <textarea
            id="task-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            placeholder="Add some details (optional)"
            rows={3}
          />

          {formError && <p className={styles.error}>{formError}</p>}

          <div className={styles.formActions}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => setShowCreateForm(false)}
            >
              Cancel
            </button>

            <button
              type="submit"
              className={styles.primaryButton}
              disabled={creating}
            >
              {creating ? "Creating..." : "Create task"}
            </button>
          </div>
        </form>
      )}

      <div className={styles.toolbar}>
        <div className={styles.filters}>
          {STATUS_OPTIONS.map((option) => (
            <button
              key={option.value}
              className={`${styles.filterButton} ${
                status === option.value ? styles.filterActive : ""
              }`}
              onClick={() => changeFilter(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>

        <div className={styles.controls}>
          <input
            className={styles.search}
            type="search"
            placeholder="Search tasks..."
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(1);
            }}
          />

          <select
            value={sort}
            onChange={(event) => changeSort(event.target.value)}
            aria-label="Sort tasks by"
          >
            <option value="created_at">Date created</option>
            <option value="title">Title</option>
          </select>

          <select
            value={order}
            onChange={(event) => changeOrder(event.target.value)}
            aria-label="Sort order"
          >
            <option value="desc">Newest first</option>
            <option value="asc">Oldest first</option>
          </select>
        </div>
      </div>

      {error && (
        <div className={styles.errorPanel}>
          <p>{error}</p>
          <button className={styles.secondaryButton} onClick={loadTodos}>
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className={styles.emptyState}>Loading tasks...</div>
      ) : !error && todos.length === 0 ? (
        <div className={styles.emptyState}>
          <h2>No tasks found</h2>
          <p>
            {search || status
              ? "Try changing your search or filters."
              : "Create your first task to get started."}
          </p>
          {!search && !status && (
            <button
              className={styles.primaryButton}
              onClick={() => setShowCreateForm(true)}
            >
              Create your first task
            </button>
          )}
        </div>
      ) : (
        <>
          <div className={styles.listHeader}>
            <span>Task</span>
            <span>Task status</span>
            <span>Assignment</span>
            <span>Created</span>
          </div>

          <div className={styles.taskList}>
            {todos.map((todo) => {
              const isCreator = user?.id === todo.creator;
              const isAssignee = user?.id === todo.assignee;

              return (
                <Link
                  href={`/todos/${todo.id}`}
                  key={todo.id}
                  className={styles.taskRow}
                >
                  <div className={styles.taskInfo}>
                    <span className={styles.taskTitle}>{todo.title}</span>
                    <span className={styles.taskMeta}>
                      {isCreator
                        ? "Created by you"
                        : isAssignee
                          ? "Assigned to you"
                          : "Task"}
                    </span>
                  </div>

                  <div>
                    <span
                      className={`${styles.status} ${
                        styles[formatStatus(todo.task_status).replaceAll(" ", "")]
                      }`}
                    >
                      {formatStatus(todo.task_status)}
                    </span>
                  </div>

                  <div>
                    {todo.assignment_status ? (
                      <span className={styles.assignmentStatus}>
                        {formatStatus(todo.assignment_status)}
                      </span>
                    ) : (
                      <span className={styles.muted}>Unassigned</span>
                    )}
                  </div>

                  <span className={styles.date}>
                    {formatDate(todo.created_at)}
                  </span>
                </Link>
              );
            })}
          </div>

          <div className={styles.pagination}>
            <button
              className={styles.secondaryButton}
              disabled={!pagination.previous || loading}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
            >
              Previous
            </button>

            <span>Page {page}</span>

            <button
              className={styles.secondaryButton}
              disabled={!pagination.next || loading}
              onClick={() => setPage((value) => value + 1)}
            >
              Next
            </button>
          </div>
        </>
      )}
    </section>
  );
}
