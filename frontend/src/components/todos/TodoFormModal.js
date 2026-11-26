"use client";

import { useMemo, useState } from "react";
import { api } from "@/lib/api";
import { PRIORITIES } from "@/lib/format";
import { useToast } from "@/components/ui/Toast";
import { Avatar, Modal } from "@/components/ui/ui";

/**
 * Create (PM) or edit (PM) a todo.
 * props: team {id,name}, members [{id,name,role}], todo?, onClose, onSaved(todo)
 */
export default function TodoFormModal({ team, members, todo, onClose, onSaved }) {
  const toast = useToast();
  const editing = Boolean(todo);

  const [title, setTitle] = useState(todo?.title ?? "");
  const [description, setDescription] = useState(todo?.description ?? "");
  const [priority, setPriority] = useState(todo?.priority ?? "MEDIUM");
  const [dueDate, setDueDate] = useState(todo?.due_date ?? "");
  const [selected, setSelected] = useState(() => new Set(todo?.assignees.map((a) => a.id) ?? []));
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const allSelected = useMemo(() => members.length > 0 && members.every((m) => selected.has(m.id)), [members, selected]);

  const toggle = (id) =>
    setSelected((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(members.map((m) => m.id)));

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!title.trim()) return setError("Please enter a title.");
    if (selected.size === 0) return setError("Assign the task to at least one member.");

    const payload = {
      title: title.trim(),
      description,
      priority,
      due_date: dueDate || null,
      assignee_ids: [...selected],
    };

    setSaving(true);
    try {
      const saved = editing
        ? await api(`/todos/${todo.id}`, { method: "PATCH", body: payload })
        : await api("/todos", { method: "POST", body: { ...payload, team_id: team.id } });
      toast.success(editing ? "Task updated." : "Task created.");
      onSaved(saved);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      wide
      title={editing ? "Edit task" : `New task in ${team.name}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="btn btn-primary" form="todo-form" disabled={saving}>
            {saving ? "Saving…" : editing ? "Save changes" : "Create task"}
          </button>
        </>
      }
    >
      <form id="todo-form" onSubmit={submit}>
        {error && <div className="error-note" role="alert" style={{ marginBottom: 14 }}>{error}</div>}

        <div className="field">
          <label className="label" htmlFor="t-title">Title</label>
          <input id="t-title" className="input" value={title} maxLength={255} autoFocus onChange={(e) => setTitle(e.target.value)} />
        </div>

        <div className="field">
          <label className="label" htmlFor="t-desc">Description</label>
          <textarea id="t-desc" className="textarea" value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>

        <div className="row">
          <div className="field">
            <label className="label" htmlFor="t-priority">Priority</label>
            <select id="t-priority" className="select" value={priority} onChange={(e) => setPriority(e.target.value)}>
              {PRIORITIES.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
            </select>
          </div>
          <div className="field">
            <label className="label" htmlFor="t-due">Due date</label>
            <input id="t-due" className="input" type="date" value={dueDate ?? ""} onChange={(e) => setDueDate(e.target.value)} />
          </div>
        </div>

        <div className="field" style={{ marginBottom: 0 }}>
          <span className="label">Assign to ({selected.size} selected)</span>
          <div className="check-list">
            <label className="check-row all">
              <input type="checkbox" checked={allSelected} onChange={toggleAll} />
              Everyone in {team.name}
            </label>
            {members.map((m) => (
              <label key={m.id} className="check-row">
                <input type="checkbox" checked={selected.has(m.id)} onChange={() => toggle(m.id)} />
                <Avatar name={m.name} />
                <span>{m.name}{m.role === "PM" ? " (you, PM)" : ""}</span>
              </label>
            ))}
          </div>
        </div>
      </form>
    </Modal>
  );
}
