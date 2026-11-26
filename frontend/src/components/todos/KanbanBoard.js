"use client";

import { useState } from "react";
import Link from "next/link";
import { STATUSES, formatDate } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";
import { AvatarStack, PriorityBadge, TeamTag } from "@/components/ui/ui";
import styles from "./Kanban.module.css";

const ORDER = STATUSES.map((s) => s.value);

function Card({ todo, showTeam, onMove, onDragStart, dragging }) {
  const index = ORDER.indexOf(todo.status);
  const canMove = todo.can_change_status;

  return (
    <article
      className={`${styles.card} ${dragging ? styles.dragging : ""}`}
      style={{ "--team": teamColor(todo.team.color) }}
      draggable={canMove}
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", String(todo.id));
        e.dataTransfer.effectAllowed = "move";
        onDragStart(todo.id);
      }}
      onDragEnd={() => onDragStart(null)}
    >
      <div className={styles.top}>
        {showTeam ? <TeamTag team={todo.team} /> : <span />}
        <PriorityBadge priority={todo.priority} />
      </div>

      <div>
        <Link href={`/todos/${todo.id}`} className={styles.title}>{todo.title}</Link>
        {todo.description && <p className={styles.desc}>{todo.description}</p>}
      </div>

      <div className={styles.meta}>
        <AvatarStack people={todo.assignees} />
        <span className={`${styles.due} ${todo.is_overdue ? styles.overdue : ""}`}>
          {todo.due_date ? `${todo.is_overdue ? "Overdue · " : "Due "}${formatDate(todo.due_date)}` : "No due date"}
        </span>
      </div>

      <div className={styles.foot}>
        {!todo.is_assignee ? <span className={styles.managing}>Managing</span> : <span />}
        {canMove && (
          <span className={styles.moves}>
            <button
              className="btn btn-sm btn-icon"
              disabled={index <= 0}
              onClick={() => onMove(todo, ORDER[index - 1])}
              aria-label="Move to previous column"
              title="Move back"
            >←</button>
            <button
              className="btn btn-sm btn-icon"
              disabled={index >= ORDER.length - 1}
              onClick={() => onMove(todo, ORDER[index + 1])}
              aria-label="Move to next column"
              title="Move forward"
            >→</button>
          </span>
        )}
      </div>
    </article>
  );
}

/** Only ever receives todos the user can change; drag between columns or use the arrows. */
export default function KanbanBoard({ todos, onMove, showTeam = true }) {
  const [dragId, setDragId] = useState(null);
  const [overCol, setOverCol] = useState(null);

  function drop(event, status) {
    event.preventDefault();
    const id = Number(event.dataTransfer.getData("text/plain"));
    setOverCol(null);
    setDragId(null);
    const todo = todos.find((t) => t.id === id);
    if (todo && todo.can_change_status) onMove(todo, status);
  }

  return (
    <div className={styles.board}>
      {STATUSES.map((col) => {
        const items = todos.filter((t) => t.status === col.value);
        return (
          <section
            key={col.value}
            className={`${styles.column} ${overCol === col.value ? styles.over : ""}`}
            style={{ "--c": `var(--${col.value === "PENDING" ? "pending" : col.value === "IN_PROGRESS" ? "progress" : "done"})` }}
            onDragOver={(e) => {
              if (dragId) {
                e.preventDefault();
                setOverCol(col.value);
              }
            }}
            onDragLeave={() => setOverCol((c) => (c === col.value ? null : c))}
            onDrop={(e) => drop(e, col.value)}
            aria-label={col.label}
          >
            <div className={styles.colHead}>
              <h3>{col.label}</h3>
              <span className={styles.num}>{items.length}</span>
            </div>
            <div className={styles.cards}>
              {items.length === 0 && <p className={styles.none}>Nothing here</p>}
              {items.map((t) => (
                <Card key={t.id} todo={t} showTeam={showTeam} onMove={onMove} onDragStart={setDragId} dragging={dragId === t.id} />
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
