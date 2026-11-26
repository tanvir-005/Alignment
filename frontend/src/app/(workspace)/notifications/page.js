"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, useFetch } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";
import { EmptyState, ErrorNote, Loading, PageHeader, Pager } from "@/components/ui/ui";
import styles from "./page.module.css";

const PAGE_SIZE = 20;

export default function NotificationsPage() {
  const router = useRouter();
  const toast = useToast();
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [page, setPage] = useState(1);

  const { data, error, loading, reload } = useFetch(
    `/notifications?limit=${PAGE_SIZE}&page=${page}${unreadOnly ? "&unread=true" : ""}`
  );

  const bump = () => window.dispatchEvent(new Event("notifications-updated"));

  async function open(n) {
    try {
      if (!n.is_read) {
        await api(`/notifications/${n.id}/read`, { method: "PATCH" });
        bump();
      }
    } catch {}
    if (n.todo_id) router.push(`/todos/${n.todo_id}`);
    else if (n.team_id) router.push(`/teams/${n.team_id}`);
    else reload({ silent: true });
  }

  async function readAll() {
    try {
      await api("/notifications/read-all", { method: "PATCH" });
      bump();
      reload({ silent: true });
      toast.success("All caught up.");
    } catch (e) {
      toast.error(e.message);
    }
  }

  return (
    <div className="page">
      <PageHeader title="Notifications" subtitle="Assignments, status changes and team updates.">
        <div className="segmented" role="group" aria-label="Filter">
          <button aria-pressed={!unreadOnly} onClick={() => { setUnreadOnly(false); setPage(1); }}>All</button>
          <button aria-pressed={unreadOnly} onClick={() => { setUnreadOnly(true); setPage(1); }}>Unread</button>
        </div>
        <button className="btn" onClick={readAll}>Mark all read</button>
      </PageHeader>

      <ErrorNote error={error} onRetry={reload} />
      <div className="card">
        {loading && !data ? (
          <Loading />
        ) : (data?.results.length ?? 0) === 0 ? (
          <EmptyState glyph="◉" title="No notifications">You are all caught up.</EmptyState>
        ) : (
          <>
            <ul className={styles.list}>
              {data.results.map((n) => (
                <li
                  key={n.id}
                  className={`${styles.item} ${n.is_read ? styles.read : styles.unread}`}
                  onClick={() => open(n)}
                >
                  <span className={styles.pip} />
                  <div className={styles.msg}>
                    <p>{n.message}</p>
                    <small>{timeAgo(n.created_at)}</small>
                  </div>
                </li>
              ))}
            </ul>
            <Pager page={page} count={data.count} pageSize={PAGE_SIZE} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
