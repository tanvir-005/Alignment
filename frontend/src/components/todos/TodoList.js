"use client";

import Link from "next/link";
import { formatDate } from "@/lib/format";
import { AvatarStack, PriorityBadge, StatusBadge, TeamTag } from "@/components/ui/ui";

export default function TodoList({ todos, showTeam = true }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>
            <th>Task</th>
            {showTeam && <th>Team</th>}
            <th>Status</th>
            <th>Priority</th>
            <th>Assignees</th>
            <th>Due</th>
          </tr>
        </thead>
        <tbody>
          {todos.map((t) => (
            <tr key={t.id}>
              <td style={{ maxWidth: 360 }}>
                <Link href={`/todos/${t.id}`} className="title-cell">{t.title}</Link>
              </td>
              {showTeam && <td><TeamTag team={t.team} /></td>}
              <td><StatusBadge status={t.status} /></td>
              <td><PriorityBadge priority={t.priority} /></td>
              <td><AvatarStack people={t.assignees} /></td>
              <td style={{ whiteSpace: "nowrap", color: t.is_overdue ? "var(--danger)" : undefined, fontWeight: t.is_overdue ? 700 : 400 }}>
                {t.due_date ? formatDate(t.due_date) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
