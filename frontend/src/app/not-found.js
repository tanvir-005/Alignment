import Link from "next/link";

export default function NotFound() {
  return (
    <main style={{ minHeight: "100vh", display: "grid", placeItems: "center", padding: 24 }}>
      <div style={{ textAlign: "center", maxWidth: 420 }}>
        <p style={{ fontSize: 64, fontWeight: 800, color: "var(--primary)", lineHeight: 1 }}>404</p>
        <h1 style={{ fontSize: 22, margin: "12px 0 8px" }}>Page not found</h1>
        <p className="muted" style={{ marginBottom: 20 }}>
          The page you are looking for does not exist, or you do not have access to it.
        </p>
        <Link href="/" className="btn btn-primary">Back to workspace</Link>
      </div>
    </main>
  );
}
