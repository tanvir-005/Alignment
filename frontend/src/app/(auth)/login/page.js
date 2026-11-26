"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import styles from "../auth.module.css";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(data.error || "Unable to sign in.");
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.card}>
      <h2>Sign in</h2>
      <p className={styles.sub}>Welcome back. Use your work email.</p>

      <form onSubmit={submit}>
        {error && <div className="error-note" role="alert" style={{ marginBottom: 14 }}>{error}</div>}

        <div className="field">
          <label className="label" htmlFor="email">Email</label>
          <input id="email" className="input" type="text" autoComplete="username" required
            value={username} onChange={(e) => setUsername(e.target.value)} />
        </div>
        <div className="field">
          <label className="label" htmlFor="password">Password</label>
          <input id="password" className="input" type="password" autoComplete="current-password" required
            value={password} onChange={(e) => setPassword(e.target.value)} />
        </div>

        <button className="btn btn-primary" style={{ width: "100%", height: 38 }} disabled={loading}>
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>

      <p className={styles.footer}>
        New here? <Link href="/register">Create an account</Link>
      </p>
    </div>
  );
}
