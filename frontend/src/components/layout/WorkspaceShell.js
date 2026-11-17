"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import styles from "./WorkspaceShell.module.css";

const navigation = [
  {
    label: "WORKSPACE",
    items: [
      { name: "My tasks", href: "/todos" },
      { name: "Notifications", href: "/notifications" },
    ],
  },
  {
    label: "MANAGEMENT",
    items: [{ name: "Administration", href: "/admin" }],
  },
];

export default function WorkspaceShell({ children }) {
  const pathname = usePathname();
  const router = useRouter();

  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  
  useEffect(() => {
    let active = true;

    async function loadUnreadCount() {
      // Do not poll while the browser tab is hidden.
      if (document.visibilityState === "hidden") return;

      try {
        const response = await fetch(
          "/api/notifications/unread-count/",
          { cache: "no-store" }
        );

        if (!response.ok) return;

        const data = await response.json();

        if (active) {
          setUnreadCount(data.unread_count ?? 0);
        }
      } catch (error) {
        console.error("Unable to load unread count:", error);
      }
    }

    function handleVisibilityChange() {
      if (document.visibilityState === "visible") {
        loadUnreadCount();
      }
    }

    loadUnreadCount();

    // Refresh every 30 seconds while the page is visible.
    const intervalId = window.setInterval(loadUnreadCount, 30000);

    window.addEventListener("notifications-updated", loadUnreadCount);
    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      active = false;
      window.clearInterval(intervalId);
      window.removeEventListener("notifications-updated", loadUnreadCount);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, [pathname]);

  useEffect(() => {
    async function loadUser() {
      try {
        const response = await fetch("/api/auth/me", {
          cache: "no-store",
        });

        if (response.status === 401) {
          router.replace("/login");
          return;
        }

        if (!response.ok) {
          throw new Error("Unable to load user profile.");
        }

        const data = await response.json();
        setUser(data);
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    }

    loadUser();
  }, [router]);

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
      });
    } finally {
      router.replace("/login");
      router.refresh();
    }
  }

  const currentPage =
    navigation
      .flatMap((section) => section.items)
      .find((item) => item.href === pathname)?.name || "Workspace";

  if (loading || !user) {
    return (
      <div className={styles.loading}>
        <span>Loading workspace...</span>
      </div>
    );
  }

  return (
    <div className={styles.shell}>
      {sidebarOpen && (
        <button
          className={styles.overlay}
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation"
        />
      )}

      <aside
        className={`${styles.sidebar} ${
          sidebarOpen ? styles.sidebarOpen : ""
        }`}
      >
        <div className={styles.brand}>
          <Link href="/todos">TODO WORKSPACE</Link>
          <span>PERSONAL PRODUCTIVITY</span>
        </div>

        <nav className={styles.navigation}>
          {navigation
          .filter(
            (section) =>
              section.label !== "MANAGEMENT" || user.role === "ADMIN"
          )
            .map((section) => (
            <div key={section.label} className={styles.navSection}>
              <p className={styles.sectionLabel}>{section.label}</p>

              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={() => setSidebarOpen(false)}
                  className={`${styles.navLink} ${
                    pathname === item.href ? styles.active : ""
                  }`}
                >
                  <span>{item.name}</span>

                  {item.href === "/notifications" && unreadCount > 0 && (
                    <span className={styles.notificationBadge}>
                      {unreadCount > 99 ? "99+" : unreadCount}
                    </span>
                  )}
                </Link>
              ))}
            </div>
          ))}
        </nav>

        <div className={styles.sidebarFooter}>
          <div className={styles.userInfo}>
            <span className={styles.userName}>
              {user.first_name || user.username}
            </span>
            <span className={styles.userEmail}>{user.email}</span>
          </div>

          <button
            className={styles.logoutButton}
            onClick={handleLogout}
          >
            Sign out
          </button>
        </div>
      </aside>

      <main className={styles.main}>
        <header className={styles.topbar}>
          <button
            className={styles.menuButton}
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation"
          >
            MENU
          </button>

          <span className={styles.breadcrumb}>
            WORKSPACE / {currentPage.toUpperCase()}
          </span>

          <span className={styles.topbarUser}>
            {user.first_name || user.username}
          </span>
        </header>

        <div className={styles.content}>{children}</div>
      </main>
    </div>
  );
}