"use client";

import { PRIORITIES, STATUSES } from "@/lib/format";

/** Controlled filter bar. `value` = {search,status,priority,team?}; teams optional. */
export default function TodoFilters({ value, onChange, teams }) {
  const set = (key) => (e) => onChange({ ...value, [key]: e.target.value });
  return (
    <div className="toolbar">
      <input
        className="input grow"
        type="search"
        placeholder="Search tasks…"
        value={value.search}
        onChange={set("search")}
        aria-label="Search tasks"
      />
      {teams && (
        <select className="select" value={value.team} onChange={set("team")} aria-label="Team">
          <option value="">All teams</option>
          {teams.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
        </select>
      )}
      <select className="select" value={value.status} onChange={set("status")} aria-label="Status">
        <option value="">Any status</option>
        {STATUSES.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
      </select>
      <select className="select" value={value.priority} onChange={set("priority")} aria-label="Priority">
        <option value="">Any priority</option>
        {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
      </select>
    </div>
  );
}

export const EMPTY_FILTERS = { search: "", status: "", priority: "", team: "" };

export function filtersToQuery(filters, extra = {}) {
  const params = new URLSearchParams();
  for (const [k, v] of Object.entries({ ...filters, ...extra })) {
    if (v !== "" && v !== null && v !== undefined) params.set(k, v);
  }
  return params.toString();
}
