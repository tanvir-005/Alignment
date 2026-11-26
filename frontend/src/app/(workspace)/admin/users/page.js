"use client";

import { useState } from "react";
import Link from "next/link";
import { api, useFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { teamColor } from "@/lib/teamColors";
import { useDebounced } from "@/lib/hooks";
import { useToast } from "@/components/ui/Toast";
import { Avatar, ConfirmDialog, EmptyState, ErrorNote, Loading, Modal, PageHeader, Pager } from "@/components/ui/ui";

const PAGE_SIZE = 20;

function AddToTeamModal({ person, onClose, onDone }) {
  const toast = useToast();
  const teams = useFetch("/teams");
  const [teamId, setTeamId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const available = (teams.data ?? []).filter((t) => !person.memberships.some((m) => m.team_id === t.id));

  async function add() {
    setBusy(true);
    setError("");
    try {
      await api(`/teams/${teamId}/members`, { method: "POST", body: { user_ids: [person.id] } });
      toast.success(`${person.name} added to the team.`);
      onDone();
    } catch (e) {
      setError(e.message);
      setBusy(false);
    }
  }

  return (
    <Modal
      title={`Add ${person.name} to a team`}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={busy}>Cancel</button>
          <button className="btn btn-primary" onClick={add} disabled={busy || !teamId}>{busy ? "Adding…" : "Add to team"}</button>
        </>
      }
    >
      {error && <div className="error-note" style={{ marginBottom: 12 }}>{error}</div>}
      {teams.loading ? <Loading /> : available.length === 0 ? (
        <p className="muted">They already belong to every team, or no teams exist yet. <Link href="/admin/teams">Manage teams</Link></p>
      ) : (
        <div className="field" style={{ marginBottom: 0 }}>
          <label className="label" htmlFor="team-pick">Team</label>
          <select id="team-pick" className="select" value={teamId} onChange={(e) => setTeamId(e.target.value)}>
            <option value="">Select a team…</option>
            {available.map((t) => <option key={t.id} value={t.id}>{t.name} (PM: {t.pm.name})</option>)}
          </select>
        </div>
      )}
    </Modal>
  );
}

export default function AdminUsersPage() {
  const toast = useToast();
  const [filter, setFilter] = useState(() =>
    typeof window !== "undefined" && window.location.search.includes("unassigned") ? "unassigned" : "all"
  );
  const [searchText, setSearchText] = useState("");
  const [page, setPage] = useState(1);
  const search = useDebounced(searchText);

  const params = new URLSearchParams({ limit: PAGE_SIZE, page, search });
  if (filter === "unassigned") params.set("unassigned", "true");
  if (filter === "inactive") params.set("active", "false");
  if (filter === "all") params.set("active", "true");
  const users = useFetch(`/users?${params}`);

  const [adding, setAdding] = useState(null);
  const [deactivating, setDeactivating] = useState(null);
  const [busy, setBusy] = useState(false);

  async function setActive(person, activate) {
    setBusy(true);
    try {
      await api(`/users/${person.id}/${activate ? "activate" : "deactivate"}`, { method: "POST" });
      toast.success(activate ? `${person.name} reactivated.` : `${person.name} deactivated.`);
      setDeactivating(null);
      users.reload({ silent: true });
    } catch (e) {
      toast.error(e.message);
      setDeactivating(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <PageHeader title="People" subtitle="People sign up themselves. You decide which team they join." />

      <div className="toolbar">
        <input className="input grow" type="search" placeholder="Search by name or email…" value={searchText} onChange={(e) => { setSearchText(e.target.value); setPage(1); }} />
        <div className="segmented" role="group" aria-label="Filter">
          {[["all", "Active"], ["unassigned", "Waiting for a team"], ["inactive", "Deactivated"]].map(([key, label]) => (
            <button key={key} aria-pressed={filter === key} onClick={() => { setFilter(key); setPage(1); }}>{label}</button>
          ))}
        </div>
      </div>

      <ErrorNote error={users.error} onRetry={users.reload} />
      <div className="card">
        {users.loading && !users.data ? (
          <Loading />
        ) : (users.data?.results.length ?? 0) === 0 ? (
          <EmptyState glyph="☺" title="No people found">
            {filter === "unassigned" ? "Everyone who signed up is already in a team." : "Try a different search."}
          </EmptyState>
        ) : (
          <>
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Person</th><th>Teams</th><th>Joined</th><th /></tr></thead>
                <tbody>
                  {users.data.results.map((u) => (
                    <tr key={u.id}>
                      <td>
                        <div className="cell-flex">
                          <Avatar name={u.name} />
                          <div><b>{u.name}</b><div className="muted" style={{ fontSize: 12 }}>{u.email}</div></div>
                        </div>
                      </td>
                      <td>
                        {u.memberships.length === 0 ? (
                          <span className={`badge badge-plain ${u.is_active ? "s-PENDING" : ""}`}>{u.is_active ? "No team yet" : "—"}</span>
                        ) : (
                          <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                            {u.memberships.map((m) => (
                              <Link key={m.team_id} href={`/admin/teams/${m.team_id}`} className="tag" style={{ "--team": teamColor(m.team_color) }}>
                                <span>{m.team_name}{m.role === "PM" ? " · PM" : ""}</span>
                              </Link>
                            ))}
                          </div>
                        )}
                      </td>
                      <td className="muted" style={{ whiteSpace: "nowrap" }}>{formatDate(u.date_joined)}</td>
                      <td style={{ textAlign: "right", whiteSpace: "nowrap" }}>
                        {u.is_active ? (
                          <>
                            <button className="btn btn-sm btn-primary" onClick={() => setAdding(u)}>Add to team</button>{" "}
                            <button className="btn btn-sm btn-danger" onClick={() => setDeactivating(u)}>Deactivate</button>
                          </>
                        ) : (
                          <button className="btn btn-sm" onClick={() => setActive(u, true)}>Reactivate</button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Pager page={page} count={users.data.count} pageSize={PAGE_SIZE} onPage={setPage} />
          </>
        )}
      </div>

      {adding && <AddToTeamModal person={adding} onClose={() => setAdding(null)} onDone={() => { setAdding(null); users.reload({ silent: true }); }} />}
      {deactivating && (
        <ConfirmDialog title={`Deactivate ${deactivating.name}?`} confirmLabel="Deactivate" danger busy={busy} onConfirm={() => setActive(deactivating, false)} onClose={() => setDeactivating(null)}>
          They will be signed out of every team and can no longer sign in. Tasks where they were the only assignee are deleted.
          A project manager cannot be deactivated until another PM replaces them.
        </ConfirmDialog>
      )}
    </div>
  );
}
