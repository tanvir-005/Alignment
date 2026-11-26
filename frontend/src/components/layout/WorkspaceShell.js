"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { UserContext } from "@/lib/user-context";
import { ToastProvider } from "@/components/ui/Toast";
import { Avatar, Loading, TeamDot } from "@/components/ui/ui";
import styles from "./WorkspaceShell.module.css";

const ADMIN_NAV = [
  { name: "Overview", href: "/admin", glyph: "▦" },
  { name: "Teams", href: "/admin/teams", glyph: "◈" },
  { name: "People", href: "/admin/users", glyph: "☺" },
  { name: "All tasks", href: "/admin/todos", glyph: "☰" },
];

export default function WorkspaceShell({ children }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);

  // Load the current user once; everything role-based hangs off it.
  useEffect(() => {
    let alive = true;
    api("/auth/me")
      .then((me) => alive && setUser(me))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  // Route guard: admins live under /admin, members never see /admin.
  useEffect(() => {
    if (!user) return;
    const inAdmin = pathname.startsWith("/admin");
    if (user.is_admin && !inAdmin && !pathname.startsWith("/todos/") && !pathname.startsWith("/teams/")) {
      router.replace("/admin");
    } else if (!user.is_admin && inAdmin) {
      router.replace("/my-tasks");
    }
  }, [user, pathname, router]);

  // Unread notifications (members only).
  useEffect(() => {
    if (!user || user.is_admin) return;
    let alive = true;
    async function load() {
      if (document.visibilityState === "hidden") return;
      try {
        const data = await api("/notifications/unread-count");
        if (alive) setUnread(data.unread_count ?? 0);
      } catch {}
    }
    load();
    const timer = setInterval(load, 30000);
    window.addEventListener("notifications-updated", load);
    document.addEventListener("visibilitychange", load);
    return () => {
      alive = false;
      clearInterval(timer);
      window.removeEventListener("notifications-updated", load);
      document.removeEventListener("visibilitychange", load);
    };
  }, [user, pathname]);

  useEffect(() => setOpen(false), [pathname]);

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.replace("/login");
    router.refresh();
  }

  if (!user) {
    return (
      <div style={{ minHeight: "100vh", display: "grid", placeItems: "center" }}>
        <Loading />
      </div>
    );
  }

  const isActive = (href) =>
    href === "/admin" ? pathname === "/admin" : pathname === href || pathname.startsWith(`${href}/`);

  const pmCount = user.pm_team_ids?.length ?? 0;
  const roleLabel = user.is_admin
    ? "Administrator"
    : pmCount
      ? `PM of ${pmCount} team${pmCount > 1 ? "s" : ""}`
      : "Member";

  const link = (href, label, extra) => (
    <Link key={href} href={href} className={`${styles.link} ${isActive(href) ? styles.active : ""}`}>
      {extra}
      <span className={styles.linkLabel}>{label}</span>
    </Link>
  );

  return (
    <UserContext.Provider value={user}>
      <ToastProvider>
        <div className={styles.shell}>
          <header className={styles.mobileBar}>
            <button className={styles.burger} onClick={() => setOpen(true)} aria-label="Open menu">☰</button>
            <span className={styles.brand}><i className={styles.mark} />Teamboard</span>
          </header>

          {open && <div className={styles.scrim} onClick={() => setOpen(false)} />}

          <aside className={`${styles.sidebar} ${open ? styles.sidebarOpen : ""}`}>
            <Link href="/" className={styles.brand}>
              <i className={styles.mark} />Teamboard
            </Link>

            <nav className={styles.nav}>
              {user.is_admin ? (
                <>
                  <p className={styles.group}>Owner</p>
                  {ADMIN_NAV.map((n) => link(n.href, n.name, <span className={styles.glyph}>{n.glyph}</span>))}
                </>
              ) : (
                <>
                  <p className={styles.group}>Workspace</p>
                  {link("/my-tasks", "My tasks", <span className={styles.glyph}>✓</span>)}
                  <Link
                    href="/notifications"
                    className={`${styles.link} ${isActive("/notifications") ? styles.active : ""}`}
                  >
                    <span className={styles.glyph}>◉</span>
                    <span className={styles.linkLabel}>Notifications</span>
                    {unread > 0 && <span className={styles.count}>{unread > 99 ? "99+" : unread}</span>}
                  </Link>

                  <p className={styles.group}>Teams</p>
                  {user.memberships.length === 0 && <p className={styles.none}>Not in a team yet</p>}
                  {user.memberships.map((m) =>
                    link(
                      `/teams/${m.team.id}`,
                      m.team.name,
                      <>
                        <TeamDot color={m.team.color} />
                        {m.role === "PM" && <span className={styles.pm}>PM</span>}
                      </>
                    )
                  )}
                </>
              )}
            </nav>

            <div className={styles.account}>
              <Avatar name={user.name} large />
              <div className={styles.who}>
                <strong>{user.name}</strong>
                <span>{roleLabel}</span>
              </div>
              <button className={styles.logout} onClick={logout} title="Sign out" aria-label="Sign out">⎋</button>
            </div>
          </aside>

          <main className={styles.main}>{children}</main>
        </div>
      </ToastProvider>
    </UserContext.Provider>
  );
}
