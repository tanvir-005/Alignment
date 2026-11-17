
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./page.module.css";
import TodoAssignmentPanel from "@/features/todos/TodoAssignmentPanel";

const TASK_STATUSES = [
  { value: "PENDING", label: "Pending" },
  { value: "IN_PROGRESS", label: "In progress" },
  { value: "COMPLETED", label: "Completed" },
];

function formatDate(value) {
  if (!value) return "—";

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export default function TodoDetailPage() {
  const { id } = useParams();

  const [todo, setTodo] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [taskStatus, setTaskStatus] = useState("PENDING");

  const loadTodo = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [todoResponse, userResponse] = await Promise.all([
        fetch(`/api/todos/${id}/`, { cache: "no-store" }),
        fetch("/api/auth/me", { cache: "no-store" }),
      ]);

      const todoData = await todoResponse.json();

      if (!todoResponse.ok) {
        throw new Error(
          todoData.detail || todoData.error || "Unable to load task."
        );
      }

      const userData = userResponse.ok
        ? await userResponse.json()
        : null;

      setTodo(todoData);
      setUser(userData);
      setTitle(todoData.title);
      setDescription(todoData.description || "");
      setTaskStatus(todoData.task_status);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadTodo();
  }, [loadTodo]);

  const isCreator = todo && user?.id === todo.creator;
  const isAssignee = todo && user?.id === todo.assignee;
  const canEdit = todo && (
    todo.assignee ? isAssignee : isCreator
  );

  async function handleSave(event) {
    event.preventDefault();

    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(`/api/todos/${id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim(),
          task_status: taskStatus,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "Unable to update task."
        );
      }

      setTodo(data);
      setSuccess("Task updated successfully.");
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) {
    return <div className={styles.state}>Loading task...</div>;
  }

  if (error && !todo) {
    return (
      <div className={styles.state}>
        <p className={styles.error}>{error}</p>
        <Link href="/todos" className={styles.backLink}>
          Back to tasks
        </Link>
      </div>
    );
  }

  if (!todo) return null;

  return (
    <section className={styles.page}>
      <Link href="/todos" className={styles.backLink}>
        ← Back to tasks
      </Link>

      <div className={styles.header}>
        <div>
          <p className={styles.eyebrow}>TASK / #{todo.id}</p>
          <h1>{todo.title}</h1>
          <p className={styles.subtitle}>
            {isCreator
              ? "Created by you"
              : isAssignee
                ? "Assigned to you"
                : "Task details"}
          </p>
        </div>

        <span className={styles.status}>
          {todo.task_status.replaceAll("_", " ").toLowerCase()}
        </span>
      </div>

      {error && <p className={styles.error}>{error}</p>}
      {success && <p className={styles.success}>{success}</p>}

      <div className={styles.content}>
        <form className={styles.mainPanel} onSubmit={handleSave}>
          <div className={styles.panelHeader}>
            <h2>Task details</h2>
            <span>{canEdit ? "Editable" : "Read only"}</span>
          </div>

          <label htmlFor="title">Title</label>
          <input
            id="title"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            disabled={!canEdit}
            maxLength={255}
            required
          />

          <label htmlFor="description">Description</label>
          <textarea
            id="description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            disabled={!canEdit}
            rows={8}
          />

          <label htmlFor="task-status">Task status</label>
          <select
            id="task-status"
            value={taskStatus}
            onChange={(event) => setTaskStatus(event.target.value)}
            disabled={!canEdit}
          >
            {TASK_STATUSES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>

          {canEdit && (
            <div className={styles.actions}>
              <button
                type="submit"
                className={styles.primaryButton}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save changes"}
              </button>
            </div>
          )}
        </form>

        <aside className={styles.sidePanel}>
          <h2>Information</h2>

          <div className={styles.infoItem}>
            <span>Creator</span>
            <strong>{todo.creator}</strong>
          </div>

          <div className={styles.infoItem}>
            <span>Assignee</span>
            <strong>{todo.assignee ?? "Unassigned"}</strong>
          </div>

          <div className={styles.infoItem}>
            <span>Assignment status</span>
            <strong>
              {todo.assignment_status
                ? todo.assignment_status.toLowerCase()
                : "Not assigned"}
            </strong>
          </div>

          <div className={styles.infoItem}>
            <span>Created</span>
            <strong>{formatDate(todo.created_at)}</strong>
          </div>

          <div className={styles.infoItem}>
            <span>Last updated</span>
            <strong>{formatDate(todo.updated_at)}</strong>
          </div>
        </aside>
        <TodoAssignmentPanel
            todo={todo}
            user={user}
            onUpdated={loadTodo}
        />
      </div>
    </section>
  );
}
