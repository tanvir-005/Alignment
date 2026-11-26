"use client";

import Link from "next/link";
import { useFetch } from "@/lib/api";
import { timeAgo } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";
import { Avatar, EmptyState, ErrorNote, Loading, PageHeader, TeamTag } from "@/components/ui/ui";
import styles from "./page.module.css";

export default function AdminOverviewPage() {
  const { data, error, loading, reload } = useFetch("/admin/overview");

  if (loading && !data) return <Loading />;
  if (error) return <div className="page"><ErrorNote error={error} onRetry={reload} /></div>;

  const { totals, status_counts: sc, teams, workload, recent_activity: recent } = data;
  const total = totals.todos || 1;
  const maxLoad = Math.max(1, ...workload.map((w) => w.open_tasks));

  const tile = (label, value, color) => (
    <div className={styles.tile} style={{ "--c": color }}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );

  return (
    <div className="page">
      <PageHeader title="Organisation overview" subtitle="You see everything here. Project managers plan the work; assignees move it.">
        <Link href="/admin/teams" className="btn btn-primary">Manage teams</Link>
      </PageHeader>

      {totals.unassigned_users > 0 && (
        <div className="warn-note" style={{ marginBottom: 16, display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, flexWrap: "wrap" }}>
          <span>
            <b>{totals.unassigned_users}</b> {totals.unassigned_users === 1 ? "person has" : "people have"} signed up and
            {totals.unassigned_users === 1 ? " is" : " are"} waiting to be added to a team.
          </span>
          <Link href="/admin/users?unassigned=1" className="btn btn-sm">Review</Link>
        </div>
      )}

      <div className={styles.tiles}>
        {tile("Teams", totals.teams, "var(--primary)")}
        {tile("Active people", totals.active_users, "#0b8f9e")}
        {tile("Waiting for a team", totals.unassigned_users, totals.unassigned_users ? "var(--pending)" : "var(--text-3)")}
        {tile("Open tasks", totals.open_todos, "var(--progress)")}
        {tile("Overdue", totals.overdue, totals.overdue ? "var(--danger)" : "var(--text-3)")}
      </div>

      <section className="card card-pad" style={{ marginBottom: 20 }}>
        <h2 className="section-title">All tasks by status</h2>
        <div className={styles.dist} role="img" aria-label="Task status distribution">
          <i style={{ width: `${(sc.PENDING / total) * 100}%`, background: "var(--pending)" }} />
          <i style={{ width: `${(sc.IN_PROGRESS / total) * 100}%`, background: "var(--progress)" }} />
          <i style={{ width: `${(sc.COMPLETED / total) * 100}%`, background: "var(--done)" }} />
        </div>
        <div className={styles.legend}>
          <span><b>{sc.PENDING}</b> Pending</span>
          <span><b>{sc.IN_PROGRESS}</b> In progress</span>
          <span><b>{sc.COMPLETED}</b> Completed</span>
        </div>
      </section>

      <div className={styles.grid}>
        <div className="stack">
          <section className="card">
            <div className="card-head"><h2>Teams</h2><Link href="/admin/teams" className="btn btn-sm">All teams</Link></div>
            {teams.length === 0 ? (
              <EmptyState glyph="◈" title="No teams yet" action={<Link href="/admin/teams" className="btn btn-primary">Create the first team</Link>}>
                Create a team and choose its project manager to get started.
              </EmptyState>
            ) : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Team</th><th>PM</th><th>Members</th><th>Progress</th></tr></thead>
                  <tbody>
                    {teams.map((t) => {
                      const c = t.todo_counts;
                      const sum = c.total || 1;
                      return (
                        <tr key={t.id}>
                          <td><Link href={`/admin/teams/${t.id}`}><TeamTag team={t} /></Link></td>
                          <td><div className="cell-flex"><Avatar name={t.pm.name} />{t.pm.name}</div></td>
                          <td>{t.member_count}</td>
                          <td>
                            <div className="cell-flex">
                              <div className={styles.bar} title={`${c.COMPLETED} of ${c.total} done`}>
                                <i style={{ width: `${(c.COMPLETED / sum) * 100}%`, background: "var(--done)" }} />
                                <i style={{ width: `${(c.IN_PROGRESS / sum) * 100}%`, background: "var(--progress)" }} />
                                <i style={{ width: `${(c.PENDING / sum) * 100}%`, background: "var(--pending)" }} />
                              </div>
                              <span className="muted">{c.COMPLETED}/{c.total}</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card">
            <div className="card-head"><h2>Open workload</h2></div>
            <div className="card-pad">
              {workload.length === 0 ? (
                <p className="muted">No open assignments.</p>
              ) : (
                <div className={styles.load}>
                  {workload.map((w) => (
                    <div key={w.user.id} style={{ display: "contents" }}>
                      <div>
                        <div className="cell-flex" style={{ marginBottom: 4 }}><Avatar name={w.user.name} />{w.user.name}</div>
                        <div className={styles.loadBar} style={{ width: `${(w.open_tasks / maxLoad) * 100}%` }} />
                      </div>
                      <b style={{ textAlign: "right" }}>{w.open_tasks}</b>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </section>
        </div>

        <section className="card">
          <div className="card-head"><h2>Recent activity</h2></div>
          {recent.length === 0 ? (
            <EmptyState title="No activity yet">Activity appears as PMs create and teams update tasks.</EmptyState>
          ) : (
            <ul className={styles.feed}>
              {recent.map((a) => (
                <li key={a.id}>
                  <Link href={`/todos/${a.todo_id}`} style={{ color: "var(--text)" }}>{a.description}</Link>
                  <small>
                    <i className="dot" style={{ "--team": teamColor(a.team.color) }} />
                    {a.team.name} · {timeAgo(a.created_at)}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
