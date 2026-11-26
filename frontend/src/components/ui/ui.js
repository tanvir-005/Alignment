"use client";

import { useEffect } from "react";
import { avatarColor, initials, priorityLabel, statusLabel } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";

export function Avatar({ name, large = false, title }) {
  return (
    <span
      className={`avatar${large ? " avatar-lg" : ""}`}
      style={{ "--av": avatarColor(name) }}
      title={title ?? name}
      aria-label={name}
    >
      {initials(name)}
    </span>
  );
}

export function AvatarStack({ people = [], max = 3 }) {
  const shown = people.slice(0, max);
  const rest = people.length - shown.length;
  return (
    <span className="avatar-stack">
      {shown.map((p) => (
        <Avatar key={p.id} name={p.name} />
      ))}
      {rest > 0 && (
        <span className="avatar avatar-more" title={people.slice(max).map((p) => p.name).join(", ")}>
          +{rest}
        </span>
      )}
    </span>
  );
}

export function StatusBadge({ status }) {
  return <span className={`badge s-${status}`}>{statusLabel(status)}</span>;
}

export function PriorityBadge({ priority }) {
  return <span className={`badge p-${priority}`}>{priorityLabel(priority)}</span>;
}

export function RoleBadge({ role }) {
  const label = role === "PM" ? "Project manager" : role === "ADMIN" ? "Admin" : "Member";
  return <span className={`badge badge-plain role-${role}`}>{label}</span>;
}

export function TeamTag({ team }) {
  if (!team) return null;
  return (
    <span className="tag" style={{ "--team": teamColor(team.color) }} title={team.name}>
      <span>{team.name}</span>
    </span>
  );
}

export function TeamDot({ color }) {
  return <i className="dot" style={{ "--team": teamColor(color) }} />;
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="Loading" />;
}

export function Loading() {
  return (
    <div className="loading-block">
      <Spinner />
    </div>
  );
}

export function EmptyState({ glyph = "◇", title, children, action }) {
  return (
    <div className="empty">
      <div className="glyph" aria-hidden="true">{glyph}</div>
      <h3>{title}</h3>
      {children && <p style={{ maxWidth: 420 }}>{children}</p>}
      {action}
    </div>
  );
}

export function PageHeader({ title, subtitle, children }) {
  return (
    <div className="page-header">
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {children && <div className="page-actions">{children}</div>}
    </div>
  );
}

export function ErrorNote({ error, onRetry }) {
  if (!error) return null;
  return (
    <div className="error-note" role="alert" style={{ display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between" }}>
      <span>{error.message || String(error)}</span>
      {onRetry && (
        <button className="btn btn-sm" onClick={() => onRetry()}>Retry</button>
      )}
    </div>
  );
}

export function Modal({ title, onClose, children, footer, wide = false }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [onClose]);

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className={`modal${wide ? " modal-wide" : ""}`} role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="btn btn-ghost btn-icon" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function ConfirmDialog({ title, children, confirmLabel = "Confirm", danger = false, busy = false, onConfirm, onClose }) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className={`btn ${danger ? "btn-danger-solid" : "btn-primary"}`} onClick={onConfirm} disabled={busy}>
            {busy ? "Working…" : confirmLabel}
          </button>
        </>
      }
    >
      {children}
    </Modal>
  );
}

export function Pager({ page, count, pageSize, onPage }) {
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (count <= pageSize) return null;
  return (
    <div className="pager">
      <span>
        Page {page} of {pages} · {count} total
      </span>
      <span style={{ display: "flex", gap: 8 }}>
        <button className="btn btn-sm" disabled={page <= 1} onClick={() => onPage(page - 1)}>Previous</button>
        <button className="btn btn-sm" disabled={page >= pages} onClick={() => onPage(page + 1)}>Next</button>
      </span>
    </div>
  );
}
