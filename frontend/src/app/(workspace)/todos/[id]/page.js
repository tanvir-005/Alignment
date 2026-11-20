
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import styles from "./page.module.css";
import TodoAssignmentPanel from "@/features/todos/TodoAssignmentPanel";

function formatDate(value) {
  if (!value) return "—";

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatStatus(value) {
  return value?.replaceAll("_", " ").toLowerCase() || "unknown";
}

function getActorName(actor) {
  if (!actor) return "Former user";

  const fullName = [actor.first_name, actor.last_name]
    .filter(Boolean)
    .join(" ")
    .trim();

  return fullName || actor.username;
}

function getEventLabel(eventType) {
  const labels = {
    CREATED: "Task created",
    UPDATED: "Task updated",
    ASSIGNED: "Task assigned",
    ASSIGNMENT_ACCEPTED: "Assignment accepted",
    ASSIGNMENT_REJECTED: "Assignment rejected",
    STATUS_CHANGED: "Status changed",
  };

  return labels[eventType] || formatStatus(eventType);
}

function getActivityDetails(activity) {
  const metadata = activity.metadata || {};

  if (activity.event_type === "STATUS_CHANGED") {
    return `${formatStatus(metadata.old_status)} → ${formatStatus(
      metadata.new_status
    )}`;
  }

  if (activity.event_type === "ASSIGNED") {
    return metadata.assignee_username
      ? `Assigned to ${metadata.assignee_username}`
      : "";
  }

  if (activity.event_type === "UPDATED" && metadata.changes) {
    return Object.keys(metadata.changes)
      .map((field) => field.replaceAll("_", " "))
      .join(", ");
  }

  return "";
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

  const [activities, setActivities] = useState([]);
  const [activityTotal, setActivityTotal] = useState(0);
  const [activityLoading, setActivityLoading] = useState(true);
  const [activityError, setActivityError] = useState("");
  const [loadingMoreActivities, setLoadingMoreActivities] = useState(false);
  const [hasMoreActivities, setHasMoreActivities] = useState(false);
  const [activityPage, setActivityPage] = useState(1);

  const loadActivities = useCallback(
    async (page = 1, append = false) => {
      if (append) {
        setLoadingMoreActivities(true);
      } else {
        setActivityLoading(true);
      }

      setActivityError("");

      try {
        const response = await fetch(
          `/api/todos/${id}/activities/?page=${page}`,
          { cache: "no-store" }
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(
            data.detail ||
              data.error ||
              "Unable to load task activity."
          );
        }

        const results = Array.isArray(data)
          ? data
          : data.results || [];
        
        setActivityTotal(
          Array.isArray(data) ? data.length : data.count || 0
        );

        setActivities((current) =>
          append ? [...current, ...results] : results
        );

        setHasMoreActivities(
          !Array.isArray(data) && Boolean(data.next)
        );

        setActivityPage(page);
      } catch (err) {
        setActivityError(
          err.message || "Unable to load task activity."
        );
      } finally {
        setActivityLoading(false);
        setLoadingMoreActivities(false);
      }
    },
    [id]
  );

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

      await loadActivities(1, false);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, [id, loadActivities]);

  useEffect(() => {
    loadTodo();
  }, [loadTodo]);

  const isCreator = todo && user?.id === todo.creator;
  const isAssignee = todo && user?.id === todo.assignee;

  const canEdit =
    todo &&
    user?.role !== "ADMIN" &&
    (todo.assignee ? isAssignee : isCreator);

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

      await loadActivities(1, false);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSaving(false);
    }
  }

  async function handleLoadMore() {
    if (!hasMoreActivities || loadingMoreActivities) return;

    await loadActivities(activityPage + 1, true);
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
          {formatStatus(todo.task_status)}
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

      <section className={styles.activityPanel}>
        <div className={styles.activityHeader}>
          <div>
            <h2>Activity</h2>
            <p>History of changes and actions on this task.</p>
          </div>

          <span className={styles.activityCount}>
            {activityTotal} activities
          </span>
        </div>

        {activityLoading ? (
          <div className={styles.activityState}>
            Loading activity...
          </div>
        ) : activityError ? (
          <div className={styles.activityState}>
            <p className={styles.error}>{activityError}</p>
            <button
              type="button"
              className={styles.loadMoreButton}
              onClick={() => loadActivities(1, false)}
            >
              Try again
            </button>
          </div>
        ) : activities.length === 0 ? (
          <div className={styles.activityState}>
            No activity recorded yet.
          </div>
        ) : (
          <>
            <ol className={styles.timeline}>
              {activities.map((activity) => {
                const details = getActivityDetails(activity);

                return (
                  <li className={styles.timelineItem} key={activity.id}>
                    <span
                      className={styles.timelineMarker}
                      aria-hidden="true"
                    />

                    <div className={styles.timelineContent}>
                      <div className={styles.timelineTop}>
                        <strong>
                          {getEventLabel(activity.event_type)}
                        </strong>
                        <time dateTime={activity.created_at}>
                          {formatDate(activity.created_at)}
                        </time>
                      </div>

                      <p className={styles.activityDescription}>
                        {activity.description}
                      </p>

                      {details && (
                        <p className={styles.activityDetails}>
                          {details}
                        </p>
                      )}

                      <span className={styles.activityActor}>
                        {getActorName(activity.actor)}
                      </span>
                    </div>
                  </li>
                );
              })}
            </ol>

            {hasMoreActivities && (
              <div className={styles.loadMoreWrapper}>
                <button
                  type="button"
                  className={styles.loadMoreButton}
                  onClick={handleLoadMore}
                  disabled={loadingMoreActivities}
                >
                  {loadingMoreActivities
                    ? "Loading..."
                    : "Load older activity"}
                </button>
              </div>
            )}
          </>
        )}
      </section>
    </section>
  );
}
