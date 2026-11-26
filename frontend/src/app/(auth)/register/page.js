"use client";

import { useState } from "react";
import Link from "next/link";
import styles from "../auth.module.css";

export default function RegisterPage() {
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  const set = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Unable to create the account.");
        return;
      }
      setDone(true);
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <div className={`${styles.card} ${styles.success}`}>
        <div className={styles.tick}>✓</div>
        <h2>Account created</h2>
        <p className={styles.sub}>
          Sign in now. An administrator will add you to a team, and your tasks
          will appear as soon as they do.
        </p>
        <Link href="/login" className="btn btn-primary" style={{ width: "100%", height: 38 }}>
          Go to sign in
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.card}>
      <h2>Create your account</h2>
      <p className={styles.sub}>An administrator will add you to a team after you sign up.</p>

      <form onSubmit={submit}>
        {error && <div className="error-note" role="alert" style={{ marginBottom: 14 }}>{error}</div>}

        <div className="field">
          <label className="label" htmlFor="name">Full name</label>
          <input id="name" className="input" required autoComplete="name" value={form.name} onChange={set("name")} />
        </div>
        <div className="field">
          <label className="label" htmlFor="email">Work email</label>
          <input id="email" className="input" type="email" required autoComplete="email" value={form.email} onChange={set("email")} />
        </div>
        <div className="field">
          <label className="label" htmlFor="password">Password</label>
          <input id="password" className="input" type="password" required autoComplete="new-password" value={form.password} onChange={set("password")} />
          <span className="hint">At least 8 characters, not too common.</span>
        </div>

        <button className="btn btn-primary" style={{ width: "100%", height: 38 }} disabled={loading}>
          {loading ? "Creating…" : "Create account"}
        </button>
      </form>

      <p className={styles.footer}>
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </div>
  );
}
