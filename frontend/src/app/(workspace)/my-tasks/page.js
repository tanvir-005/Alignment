"use client";

import { useCallback, useState } from "react";
import { useFetch } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import { useUser } from "@/lib/user-context";
import { EmptyState, ErrorNote, Loading, PageHeader, Pager } from "@/components/ui/ui";
import KanbanBoard from "@/components/todos/KanbanBoard";
import TodoList from "@/components/todos/TodoList";
import TodoFilters, { EMPTY_FILTERS, filtersToQuery } from "@/components/todos/TodoFilters";
import { useMoveTodo } from "@/components/todos/useMoveTodo";
import styles from "./page.module.css";

const PAGE_SIZE = 15;

export default function MyTasksPage() {
  const user = useUser();
  const [team, setTeam] = useState("");
  const [view, setView] = useState("board");
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const search = useDebounced(filters.search);

  const board = useFetch(
    user.has_team ? `/todos?${filtersToQuery({ team }, { scope: "actionable", limit: 500, ordering: "due" })}` : null
  );
  const others = useFetch(
    user.has_team
      ? `/todos?${filtersToQuery({ ...filters, search, team }, { scope: "other", limit: PAGE_SIZE, page })}`
      : null
  );

  const setTodos = useCallback(
    (updater) => board.setData((d) => (d ? { ...d, results: updater(d.results) } : d)),
    [board.setData] // eslint-disable-line react-hooks/exhaustive-deps
  );
  const move = useMoveTodo(setTodos);

  if (!user.has_team) {
    return (
      <div className="page">
        <PageHeader title="My tasks" />
        <div className="card">
          <EmptyState glyph="⏳" title="You are not in a team yet">
            An administrator needs to add you to a team. Once they do, the tasks
            assigned to you will show up here.
          </EmptyState>
        </div>
      </div>
    );
  }

  const mine = board.data?.results ?? [];
  const open = mine.filter((t) => t.status !== "COMPLETED");
  const stat = (label, value, color) => (
    <div className={styles.stat} style={{ "--c": color }}>
      <b>{value}</b>
      <span>{label}</span>
    </div>
  );

  return (
    <div className="page">
      <PageHeader title="My tasks" subtitle="Everything you can move forward, plus what the rest of your teams are doing.">
        <select className="select" style={{ width: "auto" }} value={team} onChange={(e) => { setTeam(e.target.value); setPage(1); }} aria-label="Filter by team">
          <option value="">All my teams</option>
          {user.memberships.map((m) => <option key={m.team.id} value={m.team.id}>{m.team.name}</option>)}
        </select>
      </PageHeader>

      <div className={styles.stats}>
        {stat("To do", mine.filter((t) => t.status === "PENDING").length, "var(--pending)")}
        {stat("In progress", mine.filter((t) => t.status === "IN_PROGRESS").length, "var(--progress)")}
        {stat("Completed", mine.filter((t) => t.status === "COMPLETED").length, "var(--done)")}
        {stat("Overdue", open.filter((t) => t.is_overdue).length, "var(--danger)")}
      </div>

      <div className={styles.sectionHead}>
        <div>
          <h2>Your board</h2>
          <p>Tasks assigned to you and tasks in teams you manage.</p>
        </div>
        <div className="segmented" role="group" aria-label="View">
          <button aria-pressed={view === "board"} onClick={() => setView("board")}>Board</button>
          <button aria-pressed={view === "list"} onClick={() => setView("list")}>List</button>
        </div>
      </div>

      <ErrorNote error={board.error} onRetry={board.reload} />
      {board.loading && !board.data ? (
        <Loading />
      ) : mine.length === 0 ? (
        <div className="card">
          <EmptyState glyph="✓" title="Nothing assigned to you">
            When a project manager assigns you work, it appears here.
          </EmptyState>
        </div>
      ) : view === "board" ? (
        <KanbanBoard todos={mine} onMove={move} />
      ) : (
        <div className="card"><TodoList todos={mine} /></div>
      )}

      <div className={styles.gap} />

      <div className={styles.sectionHead}>
        <div>
          <h2>Other tasks in your teams</h2>
          <p>Read-only: you are not assigned to these.</p>
        </div>
      </div>

      <TodoFilters value={filters} onChange={(f) => { setFilters(f); setPage(1); }} />
      <ErrorNote error={others.error} onRetry={others.reload} />
      <div className="card">
        {others.loading && !others.data ? (
          <Loading />
        ) : (others.data?.results.length ?? 0) === 0 ? (
          <EmptyState title="No other tasks">No matching tasks from your teams.</EmptyState>
        ) : (
          <>
            <TodoList todos={others.data.results} />
            <Pager page={page} count={others.data.count} pageSize={PAGE_SIZE} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
