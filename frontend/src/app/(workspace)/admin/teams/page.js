"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useFetch } from "@/lib/api";
import { teamColor } from "@/lib/teamColors";
import { Avatar, EmptyState, ErrorNote, Loading, PageHeader } from "@/components/ui/ui";
import TeamFormModal from "@/components/admin/TeamFormModal";
import styles from "./page.module.css";

export default function AdminTeamsPage() {
  const router = useRouter();
  const { data, error, loading, reload } = useFetch("/teams");
  const [creating, setCreating] = useState(false);

  return (
    <div className="page">
      <PageHeader title="Teams" subtitle="Each team runs its own project with exactly one project manager.">
        <button className="btn btn-primary" onClick={() => setCreating(true)}>+ Create team</button>
      </PageHeader>

      <ErrorNote error={error} onRetry={reload} />
      {loading && !data ? (
        <Loading />
      ) : (data?.length ?? 0) === 0 ? (
        <div className="card">
          <EmptyState glyph="◈" title="No teams yet" action={<button className="btn btn-primary" onClick={() => setCreating(true)}>Create the first team</button>}>
            Create a team, pick its project manager, then add members.
          </EmptyState>
        </div>
      ) : (
        <div className={styles.grid}>
          {data.map((t) => (
            <Link key={t.id} href={`/admin/teams/${t.id}`} className={styles.card} style={{ "--team": teamColor(t.color) }}>
              <h2>{t.name}</h2>
              <p className={styles.desc}>{t.description || "No description."}</p>
              <div className="cell-flex"><Avatar name={t.pm.name} /><span><span className="muted">PM · </span><b>{t.pm.name}</b></span></div>
              <div className={styles.counts}>
                <span><b>{t.member_count}</b> members</span>
                <span><b>{t.todo_counts.total}</b> tasks</span>
                <span><b>{t.todo_counts.COMPLETED}</b> done</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {creating && (
        <TeamFormModal
          onClose={() => setCreating(false)}
          onSaved={(team) => {
            setCreating(false);
            router.push(`/admin/teams/${team.id}`);
          }}
        />
      )}
    </div>
  );
}
