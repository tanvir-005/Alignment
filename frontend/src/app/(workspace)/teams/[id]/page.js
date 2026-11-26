"use client";

import { use, useCallback, useState } from "react";
import Link from "next/link";
import { useFetch } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import { isPmOf, useUser } from "@/lib/user-context";
import { teamColor } from "@/lib/teamColors";
import { Avatar, EmptyState, ErrorNote, Loading, Pager, RoleBadge } from "@/components/ui/ui";
import KanbanBoard from "@/components/todos/KanbanBoard";
import TodoList from "@/components/todos/TodoList";
import TodoFormModal from "@/components/todos/TodoFormModal";
import TodoFilters, { EMPTY_FILTERS, filtersToQuery } from "@/components/todos/TodoFilters";
import { useMoveTodo } from "@/components/todos/useMoveTodo";
import styles from "./page.module.css";

const PAGE_SIZE = 15;

export default function TeamPage({ params }) {
  const { id } = use(params);
  const user = useUser();
  const isPm = isPmOf(user, id);

  const [tab, setTab] = useState("board");
  const [creating, setCreating] = useState(false);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const search = useDebounced(filters.search);

  const team = useFetch(`/teams/${id}`);
  const board = useFetch(`/todos?scope=actionable&team=${id}&limit=500&ordering=due`);
  const all = useFetch(
    tab === "list" ? `/todos?${filtersToQuery({ ...filters, search, team: "" }, { team: id, limit: PAGE_SIZE, page })}` : null
  );

  const setTodos = useCallback(
    (updater) => board.setData((d) => (d ? { ...d, results: updater(d.results) } : d)),
    [board.setData] // eslint-disable-line react-hooks/exhaustive-deps
  );
  const move = useMoveTodo(setTodos, () => all.reload({ silent: true }));

  if (team.loading && !team.data) return <Loading />;
  if (team.error) {
    return (
      <div className="page">
        <ErrorNote error={team.error.status === 404 ? { message: "This team does not exist, or you are not a member of it." } : team.error} />
        <p style={{ marginTop: 14 }}><Link href="/my-tasks">← Back to my tasks</Link></p>
      </div>
    );
  }

  const t = team.data;
  const counts = t.todo_counts;
  const color = teamColor(t.color);
  const mine = board.data?.results ?? [];

  const afterSave = () => {
    setCreating(false);
    board.reload({ silent: true });
    all.reload({ silent: true });
    team.reload({ silent: true });
  };

  return (
    <div className="page">
      <div className={styles.hero} style={{ "--team": color }}>
        <div>
          <h1>{t.name}</h1>
          {t.description && <p>{t.description}</p>}
          <div className={styles.facts}>
            <div className={styles.fact}>
              <span>Project manager</span>
              <b><Avatar name={t.pm.name} /> {t.pm.name}</b>
            </div>
            <div className={styles.fact}>
              <span>Your role</span>
              <b><RoleBadge role={t.my_role} /></b>
            </div>
            <div className={styles.fact}>
              <span>Members</span>
              <b>{t.member_count}</b>
            </div>
          </div>
        </div>
        <div className={styles.counts}>
          <div className={styles.count} style={{ "--c": "var(--pending)" }}><b>{counts.PENDING}</b><span>Pending</span></div>
          <div className={styles.count} style={{ "--c": "var(--progress)" }}><b>{counts.IN_PROGRESS}</b><span>In progress</span></div>
          <div className={styles.count} style={{ "--c": "var(--done)" }}><b>{counts.COMPLETED}</b><span>Completed</span></div>
        </div>
      </div>

      <div className="page-header" style={{ marginBottom: 0 }}>
        <div className="tabs" role="tablist" style={{ flex: 1, marginBottom: 14 }}>
          {[
            ["board", isPm ? "Board" : "My board"],
            ["list", "All tasks"],
            ["members", "Members"],
          ].map(([key, label]) => (
            <button key={key} role="tab" className="tab" aria-selected={tab === key} onClick={() => setTab(key)}>
              {label}
            </button>
          ))}
        </div>
        {isPm && (
          <button className="btn btn-primary" style={{ marginBottom: 14 }} onClick={() => setCreating(true)}>
            + New task
          </button>
        )}
      </div>

      {tab === "board" && (
        <>
          <ErrorNote error={board.error} onRetry={board.reload} />
          {board.loading && !board.data ? (
            <Loading />
          ) : mine.length === 0 ? (
            <div className="card">
              <EmptyState glyph="✓" title={isPm ? "No tasks yet" : "Nothing assigned to you here"}>
                {isPm
                  ? "Create the first task and assign it to some or all of your members."
                  : "Tasks the PM assigns to you appear on this board. Others are under “All tasks”."}
              </EmptyState>
            </div>
          ) : (
            <KanbanBoard todos={mine} onMove={move} showTeam={false} />
          )}
        </>
      )}

      {tab === "list" && (
        <>
          <TodoFilters value={filters} onChange={(f) => { setFilters(f); setPage(1); }} />
          <ErrorNote error={all.error} onRetry={all.reload} />
          <div className="card">
            {all.loading && !all.data ? (
              <Loading />
            ) : (all.data?.results.length ?? 0) === 0 ? (
              <EmptyState title="No tasks found">Try changing your filters.</EmptyState>
            ) : (
              <>
                <TodoList todos={all.data.results} showTeam={false} />
                <Pager page={page} count={all.data.count} pageSize={PAGE_SIZE} onPage={setPage} />
              </>
            )}
          </div>
        </>
      )}

      {tab === "members" && (
        <div className="card">
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Member</th><th>Role</th><th>Open tasks</th></tr></thead>
              <tbody>
                {t.members.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <div className="cell-flex">
                        <Avatar name={m.name} />
                        <div>
                          <b>{m.name}{m.id === user.id ? " (you)" : ""}</b>
                          <div className="muted" style={{ fontSize: 12 }}>{m.email}</div>
                        </div>
                      </div>
                    </td>
                    <td><RoleBadge role={m.role} /></td>
                    <td>{m.open_tasks}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pager" style={{ justifyContent: "flex-start" }}>
            Members are added and removed by an administrator.
          </div>
        </div>
      )}

      {creating && (
        <TodoFormModal team={t} members={t.members} onClose={() => setCreating(false)} onSaved={afterSave} />
      )}
    </div>
  );
}
