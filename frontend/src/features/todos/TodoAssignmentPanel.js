
"use client";

import { useEffect, useState } from "react";
import styles from "./TodoAssignmentPanel.module.css";

export default function TodoAssignmentPanel({ todo, user, onUpdated }) {
  const [members, setMembers] = useState([]);
  const [selectedAssignee, setSelectedAssignee] = useState("");
  const [loadingMembers, setLoadingMembers] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const isAdmin = user?.role === "ADMIN";
  const isCreator = !isAdmin && user?.id === todo.creator;
  const isAssignee = !isAdmin && user?.id === todo.assignee;
  const isPending = todo.assignment_status === "PENDING";

  useEffect(() => {
    async function loadMembers() {
      if (isAdmin || !todo.team) {
        setLoadingMembers(false);
        return;
      }

      try {
        const response = await fetch("/api/teams/", {
          cache: "no-store",
        });

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || data.error || "Unable to load teammates.");
        }

        const teams = Array.isArray(data) ? data : data.results || [];
        const currentTeam = teams.find(
          (team) => team.id === todo.team
        );

        setMembers(
          (currentTeam?.members || []).filter(
            (member) => member.id !== user?.id
          )
        );
      } catch (err) {
        setError(err.message || "Unable to load teammates.");
      } finally {
        setLoadingMembers(false);
      }
    }

    loadMembers();
  }, [todo.team, user?.id, isAdmin]);

  async function handleAction(url, decision = null) {
    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        ...(decision && {
          body: JSON.stringify({ decision }),
        }),
        ...(url.endsWith("/assign/") && {
          body: JSON.stringify({
            assignee: Number(selectedAssignee),
          }),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail || data.error || "The operation failed."
        );
      }

      setSuccess(
        decision
            ? `Assignment ${decision.toLowerCase()}.`
            : "Task assigned successfully."
        );

      // Notify the workspace shell to refresh its unread count.
      window.dispatchEvent(new Event("notifications-updated"));
  
      await onUpdated();
    } catch (err) {
      setError(err.message || "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className={styles.panel}>
      <div className={styles.header}>
        <h2>Assignment</h2>
        <span>
          {todo.assignment_status
            ? todo.assignment_status.toLowerCase()
            : "Not assigned"}
        </span>
      </div>

      {isAdmin ? (
        <p className={styles.description}>
          Read-only inspection. Administrators cannot change task assignments.
        </p>
      ) : todo.assignee ? (
        <div className={styles.assigneeInfo}>
          <span>Assigned to</span>
          <strong>
            {isAssignee ? "You" : `User #${todo.assignee}`}
          </strong>
        </div>
      ) : (
        <p className={styles.description}>
          This task has not been assigned to anyone.
        </p>
      )}

      {isCreator && !todo.assignee && (
        <div className={styles.assignForm}>
          {!todo.team ? (
            <p className={styles.description}>
              This task has no team. Assignment is unavailable.
            </p>
          ) : loadingMembers ? (
            <p className={styles.description}>Loading teammates...</p>
          ) : members.length === 0 ? (
            <p className={styles.description}>
              No teammates available for assignment.
            </p>
          ) : (
            <>
              <label htmlFor="assignee">Choose a teammate</label>

              <select
                id="assignee"
                value={selectedAssignee}
                onChange={(event) => setSelectedAssignee(event.target.value)}
              >
                <option value="">Select a teammate</option>

                {members.map((member) => (
                  <option key={member.id} value={member.id}>
                    {member.first_name || member.username}{" "}
                    {member.last_name || ""}
                  </option>
                ))}
              </select>

              <button
                className={styles.primaryButton}
                disabled={!selectedAssignee || submitting}
                onClick={() => handleAction(`/api/todos/${todo.id}/assign/`)}
              >
                {submitting ? "Assigning..." : "Assign task"}
              </button>
            </>
          )}
        </div>
      )}

      {isAssignee && isPending && (
        <div className={styles.responseActions}>
          <p className={styles.description}>
            You have been assigned this task. Accept or reject the assignment.
          </p>

          <button
            className={styles.primaryButton}
            disabled={submitting}
            onClick={() =>
              handleAction(
                `/api/todos/${todo.id}/respond/`,
                "ACCEPTED"
              )
            }
          >
            Accept
          </button>

          <button
            className={styles.secondaryButton}
            disabled={submitting}
            onClick={() =>
              handleAction(
                `/api/todos/${todo.id}/respond/`,
                "REJECTED"
              )
            }
          >
            Reject
          </button>
        </div>
      )}

      {error && <p className={styles.error}>{error}</p>}
      {success && <p className={styles.success}>{success}</p>}
    </section>
  );
}
