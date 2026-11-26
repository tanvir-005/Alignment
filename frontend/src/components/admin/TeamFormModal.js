"use client";

import { useState } from "react";
import { api, useFetch } from "@/lib/api";
import { TEAM_COLOR_KEYS, teamColor } from "@/lib/teamColors";
import { useToast } from "@/components/ui/Toast";
import { Modal } from "@/components/ui/ui";

/** Create a team (name, colour, PM) or edit its name / description / colour. */
export default function TeamFormModal({ team, onClose, onSaved }) {
  const toast = useToast();
  const editing = Boolean(team);

  const [name, setName] = useState(team?.name ?? "");
  const [description, setDescription] = useState(team?.description ?? "");
  const [color, setColor] = useState(team?.color ?? "blue");
  const [pmId, setPmId] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  const users = useFetch(editing ? null : "/users?active=true&limit=200");

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (!name.trim()) return setError("Please enter a team name.");
    if (!editing && !pmId) return setError("Choose a project manager. Every team needs one.");

    setSaving(true);
    try {
      const saved = editing
        ? await api(`/teams/${team.id}`, { method: "PATCH", body: { name: name.trim(), description, color } })
        : await api("/teams", {
            method: "POST",
            body: { name: name.trim(), description, color, pm_id: Number(pmId) },
          });
      toast.success(editing ? "Team updated." : "Team created.");
      onSaved(saved);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal
      title={editing ? "Edit team" : "Create team"}
      onClose={onClose}
      footer={
        <>
          <button className="btn" onClick={onClose} disabled={saving}>Cancel</button>
          <button className="btn btn-primary" form="team-form" disabled={saving}>
            {saving ? "Saving…" : editing ? "Save changes" : "Create team"}
          </button>
        </>
      }
    >
      <form id="team-form" onSubmit={submit}>
        {error && <div className="error-note" role="alert" style={{ marginBottom: 14 }}>{error}</div>}

        <div className="field">
          <label className="label" htmlFor="team-name">Team name</label>
          <input id="team-name" className="input" value={name} maxLength={100} autoFocus onChange={(e) => setName(e.target.value)} />
        </div>

        <div className="field">
          <label className="label" htmlFor="team-desc">Description</label>
          <textarea id="team-desc" className="textarea" style={{ minHeight: 70 }} value={description} onChange={(e) => setDescription(e.target.value)} />
          <span className="hint">What project does this team run?</span>
        </div>

        <div className="field">
          <span className="label">Colour</span>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            {TEAM_COLOR_KEYS.map((key) => (
              <button
                type="button"
                key={key}
                onClick={() => setColor(key)}
                aria-label={key}
                aria-pressed={color === key}
                style={{
                  width: 28, height: 28, borderRadius: 4, cursor: "pointer", background: teamColor(key),
                  border: color === key ? "2px solid var(--text)" : "2px solid transparent",
                  outline: color === key ? "2px solid var(--surface)" : "none", outlineOffset: -4,
                }}
              />
            ))}
          </div>
        </div>

        {!editing && (
          <div className="field" style={{ marginBottom: 0 }}>
            <label className="label" htmlFor="team-pm">Project manager</label>
            <select id="team-pm" className="select" value={pmId} onChange={(e) => setPmId(e.target.value)} disabled={users.loading}>
              <option value="">{users.loading ? "Loading people…" : "Select a person…"}</option>
              {(users.data?.results ?? []).map((u) => (
                <option key={u.id} value={u.id}>
                  {u.name} — {u.email}{u.memberships.length === 0 ? " (no team yet)" : ""}
                </option>
              ))}
            </select>
            <span className="hint">They become a member of this team automatically. Only an admin can change the PM later.</span>
          </div>
        )}
      </form>
    </Modal>
  );
}
