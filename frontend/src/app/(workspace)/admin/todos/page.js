"use client";

import { useState } from "react";
import { useFetch } from "@/lib/api";
import { useDebounced } from "@/lib/hooks";
import { EmptyState, ErrorNote, Loading, PageHeader, Pager } from "@/components/ui/ui";
import TodoList from "@/components/todos/TodoList";
import TodoFilters, { EMPTY_FILTERS, filtersToQuery } from "@/components/todos/TodoFilters";

const PAGE_SIZE = 20;

export default function AdminTodosPage() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const search = useDebounced(filters.search);
  const teams = useFetch("/teams");
  const todos = useFetch(`/todos?${filtersToQuery({ ...filters, search }, { limit: PAGE_SIZE, page })}`);

  return (
    <div className="page">
      <PageHeader title="All tasks" subtitle="Read-only view across every team. Admins observe; PMs and assignees do the work." />
      <TodoFilters value={filters} onChange={(f) => { setFilters(f); setPage(1); }} teams={teams.data ?? []} />
      <ErrorNote error={todos.error} onRetry={todos.reload} />
      <div className="card">
        {todos.loading && !todos.data ? (
          <Loading />
        ) : (todos.data?.results.length ?? 0) === 0 ? (
          <EmptyState title="No tasks found">Try changing your filters.</EmptyState>
        ) : (
          <>
            <TodoList todos={todos.data.results} />
            <Pager page={page} count={todos.data.count} pageSize={PAGE_SIZE} onPage={setPage} />
          </>
        )}
      </div>
    </div>
  );
}
