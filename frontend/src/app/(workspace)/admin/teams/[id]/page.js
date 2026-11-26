"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, useFetch } from "@/lib/api";
import { plural } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";
import { useDebounced } from "@/lib/hooks";
import { useToast } from "@/components/ui/Toast";
import { Avatar, ConfirmDialog, EmptyState, ErrorNote, Loading, Modal, Pager, RoleBadge } from "@/components/ui/ui";
import TeamFormModal from "@/components/admin/TeamFormModal";
import TodoList from "@/components/todos/TodoList";
import TodoFilters, { EMPTY_FILTERS, filtersToQuery } from "@/components/todos/TodoFilters";

const PAGE_SIZE = 15;

function AddMembersModal({ team, onClose, onDone }) {
  const toast = useToast();
  const [search, setSearch] = useState("");
  const q = useDebounced(search);
  const users = useFetch(`/users?active=true&exclude_team=${team.id}&limit=200&search=${encodeURIComponent(q)}`);
  const [selected, setSelected] = useState(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const toggle = (id) =>
    setSelected((s) => {
      const n = new Set(s);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });

  async function add() {
    setBusy(true);
    setError("");
    try {
      const updated = await api(`/teams/${team.id}/members`, { method: "POST", body: { user_ids: [...selected] } });
      toast.success(`${plural(selected.size, "member")} added.`);
      onDone(updated);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Add members to ${team.name}`}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" onClick={add} disabled={busy || selected.size === 0}>
            {busy ? "Adding…" : `Add ${selected.size || ""}`.trim()}
          </button>
        </>
      }
    >
      {error && <div className="error-note" style={{ marginBottom: 12 }}>{error}</div>}
      <input className="input" type="search" placeholder="Search people…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ marginBottom: 12 }} />
      {users.loading && !users.data ? (
        <Loading />
      ) : (users.data?.results.length ?? 0) === 0 ? (
        <p className="muted">No one else to add.</p>
      ) : (
        <div className="check-list" style={{ maxHeight: 320 }}>
          {users.data.results.map((u) => (
            <label key={u.id} className="check-row">
              <input type="checkbox" checked={selected.has(u.id)} onChange={() => toggle(u.id)} />
              <Avatar name={u.name} />
              <span style={{ flex: 1 }}>
                {u.name}
                <span className="muted" style={{ display: "block", fontSize: 12 }}>{u.email}</span>
              </span>
              {u.memberships.length === 0 && <span className="badge s-PENDING badge-plain">No team</span>}
            </label>
          ))}
        </div>
      )}
    </Modal>
  );
}

function ReplacePmModal({ team, onClose, onDone }) {
  const toast = useToast();
  const outsiders = useFetch(`/users?active=true&exclude_team=${team.id}&limit=200`);
  const [pmId, setPmId] = useState("");
  const [oldAction, setOldAction] = useState("member");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const candidates = team.members.filter((m) => m.role !== "PM");

  async function submit() {
    if (!pmId) return setError("Choose the new project manager.");
    setBusy(true);
    setError("");
    try {
      const updated = await api(`/teams/${team.id}/replace-pm`, {
        method: "POST",
        body: { pm_id: Number(pmId), old_pm_action: oldAction },
      });
      toast.success("Project manager replaced.");
      onDone(updated);
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      title="Replace project manager"
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? "Replacing…" : "Replace PM"}</button>
        </>
      }
    >
      {error && <div className="error-note" style={{ marginBottom: 12 }}>{error}</div>}
      <p className="muted" style={{ marginBottom: 14 }}>
        A team always has exactly one PM, so the swap happens in one step. Current PM: <b style={{ color: "var(--text)" }}>{team.pm.name}</b>.
      </p>

      <div className="field">
        <label className="label" htmlFor="new-pm">New project manager</label>
        <select id="new-pm" className="select" value={pmId} onChange={(e) => setPmId(e.target.value)}>
          <option value="">Select a person…</option>
          {candidates.length > 0 && (
            <optgroup label="Team members">
              {candidates.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </optgroup>
          )}
          {(outsiders.data?.results.length ?? 0) > 0 && (
            <optgroup label="Not in this team (will be added)">
              {outsiders.data.results.map((u) => <option key={u.id} value={u.id}>{u.name} — {u.email}</option>)}
            </optgroup>
          )}
        </select>
      </div>

      <div className="field" style={{ marginBottom: 0 }}>
        <span className="label">What happens to {team.pm.name}?</span>
        <label className="check-row" style={{ border: "1px solid var(--border)", borderRadius: 5 }}>
          <input type="radio" name="old" checked={oldAction === "member"} onChange={() => setOldAction("member")} />
          <span>Stay in the team as a regular member</span>
        </label>
        <label className="check-row" style={{ border: "1px solid var(--border)", borderRadius: 5 }}>
          <input type="radio" name="old" checked={oldAction === "remove"} onChange={() => setOldAction("remove")} />
          <span>Leave the team <span className="muted">(tasks only they are assigned to are deleted)</span></span>
        </label>
      </div>
    </Modal>
  );
}

export default function AdminTeamPage({ params }) {
  const { id } = use(params);
  const router = useRouter();
  const toast = useToast();

  const team = useFetch(`/teams/${id}`);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const search = useDebounced(filters.search);
  const todos = useFetch(`/todos?${filtersToQuery({ ...filters, search, team: "" }, { team: id, limit: PAGE_SIZE, page })}`);

  const [modal, setModal] = useState(null); // edit | add | replace | delete
  const [removal, setRemoval] = useState(null); // {member, impact}
  const [busy, setBusy] = useState(false);

  if (team.loading && !team.data) return <Loading />;
  if (team.error) {
    return (
      <div className="page">
        <ErrorNote error={team.error} />
        <p style={{ marginTop: 14 }}><Link href="/admin/teams">← All teams</Link></p>
      </div>
    );
  }
  const t = team.data;

  const refresh = (updated) => {
    if (updated) team.setData(updated);
    team.reload({ silent: true });
    todos.reload({ silent: true });
  };

  async function askRemove(member) {
    try {
      const impact = await api(`/teams/${t.id}/members/${member.id}/impact`);
      setRemoval({ member, impact });
    } catch (e) {
      toast.error(e.message);
    }
  }

  async function confirmRemove() {
    setBusy(true);
    try {
      const result = await api(`/teams/${t.id}/members/${removal.member.id}`, { method: "DELETE" });
      toast.success(
        result.deleted_todos
          ? `${removal.member.name} removed. ${plural(result.deleted_todos, "task")} deleted.`
          : `${removal.member.name} removed.`
      );
      setRemoval(null);
      refresh();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function deleteTeam() {
    setBusy(true);
    try {
      await api(`/teams/${t.id}`, { method: "DELETE" });
      toast.success("Team deleted.");
      router.replace("/admin/teams");
    } catch (e) {
      toast.error(e.message);
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <Link href="/admin/teams" style={{ fontSize: 13 }}>← All teams</Link>

      <div
        className="card"
        style={{ margin: "14px 0 22px", padding: "18px 22px", borderLeft: `6px solid ${teamColor(t.color)}`, display: "flex", gap: 16, justifyContent: "space-between", alignItems: "center", flexWrap: "wrap" }}
      >
        <div>
          <h1 style={{ fontSize: 22 }}>{t.name}</h1>
          {t.description && <p className="muted" style={{ marginTop: 4 }}>{t.description}</p>}
          <p style={{ marginTop: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <span className="muted">Project manager</span> <Avatar name={t.pm.name} /> <b>{t.pm.name}</b>
          </p>
        </div>
        <div className="page-actions">
          <button className="btn" onClick={() => setModal("edit")}>Edit</button>
          <button className="btn btn-danger" onClick={() => setModal("delete")}>Delete team</button>
        </div>
      </div>

      <div className="stack">
        <section className="card">
          <div className="card-head">
            <h2>Members ({t.member_count})</h2>
            <div style={{ display: "flex", gap: 8 }}>
              <button className="btn btn-sm" onClick={() => setModal("replace")}>Replace PM</button>
              <button className="btn btn-sm btn-primary" onClick={() => setModal("add")}>+ Add members</button>
            </div>
          </div>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Person</th><th>Role</th><th>Open tasks</th><th /></tr></thead>
              <tbody>
                {t.members.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <div className="cell-flex">
                        <Avatar name={m.name} />
                        <div><b>{m.name}</b><div className="muted" style={{ fontSize: 12 }}>{m.email}</div></div>
                      </div>
                    </td>
                    <td><RoleBadge role={m.role} /></td>
                    <td>{m.open_tasks}</td>
                    <td style={{ textAlign: "right" }}>
                      {m.role === "PM" ? (
                        <span className="muted" style={{ fontSize: 12 }}>Replace the PM to remove</span>
                      ) : (
                        <button className="btn btn-sm btn-danger" onClick={() => askRemove(m)}>Remove</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section>
          <h2 className="section-title">Tasks (read-only)</h2>
          <TodoFilters value={filters} onChange={(f) => { setFilters(f); setPage(1); }} />
          <div className="card">
            {todos.loading && !todos.data ? (
              <Loading />
            ) : (todos.data?.results.length ?? 0) === 0 ? (
              <EmptyState title="No tasks">The project manager has not created any matching tasks.</EmptyState>
            ) : (
              <>
                <TodoList todos={todos.data.results} showTeam={false} />
                <Pager page={page} count={todos.data.count} pageSize={PAGE_SIZE} onPage={setPage} />
              </>
            )}
          </div>
        </section>
      </div>

      {modal === "edit" && <TeamFormModal team={t} onClose={() => setModal(null)} onSaved={(u) => { setModal(null); refresh(u); }} />}
      {modal === "add" && <AddMembersModal team={t} onClose={() => setModal(null)} onDone={(u) => { setModal(null); refresh(u); }} />}
      {modal === "replace" && <ReplacePmModal team={t} onClose={() => setModal(null)} onDone={(u) => { setModal(null); refresh(u); }} />}

      {modal === "delete" && (
        <ConfirmDialog title={`Delete ${t.name}?`} confirmLabel="Delete team" danger busy={busy} onConfirm={deleteTeam} onClose={() => setModal(null)}>
          This removes the team, all {plural(t.todo_counts.total, "task")} in it and every membership. This cannot be undone.
        </ConfirmDialog>
      )}

      {removal && (
        <ConfirmDialog title={`Remove ${removal.member.name}?`} confirmLabel="Remove from team" danger busy={busy} onConfirm={confirmRemove} onClose={() => setRemoval(null)}>
          <p>
            {removal.member.name} is assigned to {plural(removal.impact.assigned, "task")} in {t.name}.
            They will be unassigned from all of them.
          </p>
          {removal.impact.to_delete > 0 ? (
            <p className="warn-note" style={{ marginTop: 12 }}>
              <b>{plural(removal.impact.to_delete, "task")}</b> {removal.impact.to_delete === 1 ? "has" : "have"} no other assignee
              and will be <b>deleted</b>.
            </p>
          ) : (
            <p className="muted" style={{ marginTop: 12 }}>No tasks will be deleted.</p>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}
