"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, useFetch } from "@/lib/api";
import { STATUSES, formatDate, formatDateTime } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";
import { useUser } from "@/lib/user-context";
import { useToast } from "@/components/ui/Toast";
import { Avatar, ConfirmDialog, ErrorNote, Loading, PriorityBadge, StatusBadge, TeamTag } from "@/components/ui/ui";
import TodoFormModal from "@/components/todos/TodoFormModal";
import styles from "./page.module.css";

export default function TodoDetailPage({ params }) {
  const { id } = use(params);
  const user = useUser();
  const router = useRouter();
  const toast = useToast();

  const todo = useFetch(`/todos/${id}`);
  const activity = useFetch(`/todos/${id}/activities`);
  const t = todo.data;
  const team = useFetch(t?.can_edit ? `/teams/${t.team.id}` : null);

  const [editing, setEditing] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);

  const backHref = user.is_admin ? `/admin/teams/${t?.team.id ?? ""}` : `/teams/${t?.team.id ?? ""}`;

  if (todo.loading && !t) return <Loading />;
  if (todo.error) {
    return (
      <div className="page">
        <ErrorNote error={todo.error.status === 404 ? { message: "This task does not exist, or you cannot access it." } : todo.error} />
        <p style={{ marginTop: 14 }}><Link href="/">← Back</Link></p>
      </div>
    );
  }

  async function setStatus(status) {
    if (status === t.status) return;
    setBusy(true);
    try {
      const updated = await api(`/todos/${t.id}/status`, { method: "PATCH", body: { status } });
      todo.setData(updated);
      activity.reload({ silent: true });
      toast.success("Status updated.");
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    try {
      await api(`/todos/${t.id}`, { method: "DELETE" });
      toast.success("Task deleted.");
      router.replace(backHref);
    } catch (e) {
      toast.error(e.message);
      setBusy(false);
      setDeleting(false);
    }
  }

  return (
    <div className="page">
      <Link href={backHref} className={styles.back}>← {t.team.name}</Link>

      <div className={styles.head} style={{ "--team": teamColor(t.team.color) }}>
        <div className={styles.badges}>
          <TeamTag team={t.team} />
          <PriorityBadge priority={t.priority} />
          {t.is_overdue && <span className="badge p-HIGH">Overdue</span>}
        </div>
        <h1>{t.title}</h1>

        <div className={styles.status}>
          {t.can_change_status ? (
            <>
              <div className="segmented" role="group" aria-label="Status">
                {STATUSES.map((s) => (
                  <button key={s.value} aria-pressed={t.status === s.value} disabled={busy} onClick={() => setStatus(s.value)}>
                    {s.label}
                  </button>
                ))}
              </div>
              <small>You can change this status.</small>
            </>
          ) : (
            <>
              <StatusBadge status={t.status} />
              <small>
                {user.is_admin
                  ? "Read-only: administrators observe but do not change tasks."
                  : "Only assignees and the project manager can change the status."}
              </small>
            </>
          )}
        </div>
      </div>

      <div className={styles.layout}>
        <div className="stack">
          <section className="card">
            <div className="card-head">
              <h2>Description</h2>
              {t.can_edit && (
                <div style={{ display: "flex", gap: 8 }}>
                  <button className="btn btn-sm" onClick={() => setEditing(true)} disabled={!team.data}>Edit</button>
                  <button className="btn btn-sm btn-danger" onClick={() => setDeleting(true)}>Delete</button>
                </div>
              )}
            </div>
            <div className="card-pad">
              {t.description ? <p className={styles.desc}>{t.description}</p> : <p className="muted">No description.</p>}
            </div>
          </section>

          <section className="card">
            <div className="card-head"><h2>Activity</h2></div>
            <div className="card-pad">
              {activity.loading && !activity.data ? (
                <Loading />
              ) : (
                <ul className={styles.timeline}>
                  {(activity.data ?? []).map((a) => (
                    <li key={a.id} className={styles[`ev-${a.event_type}`]}>
                      {a.description}
                      <time>{formatDateTime(a.created_at)}</time>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </section>
        </div>

        <aside className="card card-pad">
          <dl className={styles.meta} style={{ margin: 0 }}>
            <div>
              <dt>Assignees</dt>
              <dd>
                <div className={styles.people}>
                  {t.assignees.map((a) => (
                    <div key={a.id} className={styles.person}>
                      <Avatar name={a.name} />
                      <span>{a.name}{a.id === user.id ? " (you)" : ""}</span>
                    </div>
                  ))}
                </div>
              </dd>
            </div>
            <div><dt>Due date</dt><dd style={{ color: t.is_overdue ? "var(--danger)" : undefined, fontWeight: t.is_overdue ? 700 : 400 }}>{formatDate(t.due_date)}</dd></div>
            <div><dt>Created by</dt><dd>{t.created_by ? <><Avatar name={t.created_by.name} /> {t.created_by.name}</> : "—"}</dd></div>
            <div><dt>Created</dt><dd>{formatDateTime(t.created_at)}</dd></div>
            <div><dt>Last updated</dt><dd>{formatDateTime(t.updated_at)}</dd></div>
            {t.completed_at && <div><dt>Completed</dt><dd>{formatDateTime(t.completed_at)}</dd></div>}
          </dl>
        </aside>
      </div>

      {editing && team.data && (
        <TodoFormModal
          team={team.data}
          members={team.data.members}
          todo={t}
          onClose={() => setEditing(false)}
          onSaved={(saved) => {
            setEditing(false);
            todo.setData(saved);
            activity.reload({ silent: true });
          }}
        />
      )}

      {deleting && (
        <ConfirmDialog title="Delete this task?" confirmLabel="Delete task" danger busy={busy} onConfirm={remove} onClose={() => setDeleting(false)}>
          “{t.title}” will be removed for everyone on the team. This cannot be undone.
        </ConfirmDialog>
      )}
    </div>
  );
}
