
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import styles from "./page.module.css";

function formatDate(value) {
  if (!value) return "—";

  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [updating, setUpdating] = useState(false);

  const loadNotifications = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [listResponse, countResponse] = await Promise.all([
        fetch("/api/notifications/", { cache: "no-store" }),
        fetch("/api/notifications/unread-count/", {
          cache: "no-store",
        }),
      ]);

      const listData = await listResponse.json();
      const countData = await countResponse.json();

      if (!listResponse.ok) {
        throw new Error(
          listData.detail ||
            listData.error ||
            "Unable to load notifications."
        );
      }

      if (!countResponse.ok) {
        throw new Error(
          countData.detail ||
            countData.error ||
            "Unable to load unread count."
        );
      }

      setNotifications(Array.isArray(listData) ? listData : []);
      setUnreadCount(countData.unread_count ?? 0);
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  async function markAsRead(notificationId) {
    setUpdating(true);
    setError("");

    try {
      const response = await fetch(
        `/api/notifications/${notificationId}/read/`,
        { method: "PATCH" }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "Unable to update notification."
        );
      }

      window.dispatchEvent(new Event("notifications-updated"));
      await loadNotifications();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setUpdating(false);
    }
  }

  async function markAllAsRead() {
    setUpdating(true);
    setError("");

    try {
      const response = await fetch("/api/notifications/read-all/", {
        method: "POST",
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "Unable to update notifications."
        );
      }

      window.dispatchEvent(new Event("notifications-updated"));
      await loadNotifications();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setUpdating(false);
    }
  }

  return (
    <section className={styles.page}>
      <header className={styles.header}>
        <div>
          <p className={styles.eyebrow}>WORKSPACE / ACTIVITY</p>
          <h1>Notifications</h1>
          <p className={styles.subtitle}>
            Updates about your tasks and assignments.
          </p>
        </div>

        <div className={styles.headerActions}>
          <span className={styles.count}>
            {unreadCount} unread
          </span>

          <button
            className={styles.secondaryButton}
            onClick={markAllAsRead}
            disabled={updating || unreadCount === 0}
          >
            Mark all as read
          </button>
        </div>
      </header>

      {error && (
        <div className={styles.errorPanel}>
          <p>{error}</p>
          <button
            className={styles.secondaryButton}
            onClick={loadNotifications}
          >
            Retry
          </button>
        </div>
      )}

      {loading ? (
        <div className={styles.emptyState}>Loading notifications...</div>
      ) : !error && notifications.length === 0 ? (
        <div className={styles.emptyState}>
          <h2>No notifications</h2>
          <p>Updates about your tasks will appear here.</p>
        </div>
      ) : (
        <div className={styles.list}>
          {notifications.map((notification) => (
            <article
              key={notification.id}
              className={`${styles.notification} ${
                !notification.is_read ? styles.unread : ""
              }`}
            >
              <div className={styles.indicator}>
                {!notification.is_read && (
                  <span className={styles.dot} />
                )}
              </div>

              <div className={styles.content}>
                <p className={styles.message}>
                  {notification.message}
                </p>

                <div className={styles.meta}>
                  <span>{formatDate(notification.created_at)}</span>
                  <span>Task: {notification.todo_title}</span>
                </div>

                <div className={styles.actions}>
                  <Link href={`/todos/${notification.todo}`}>
                    View task
                  </Link>

                  {!notification.is_read && (
                    <button
                      onClick={() => markAsRead(notification.id)}
                      disabled={updating}
                    >
                      Mark as read
                    </button>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
