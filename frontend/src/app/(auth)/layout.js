import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import styles from "./auth.module.css";

export default async function AuthLayout({ children }) {
  const store = await cookies();
  if (store.get("access_token") || store.get("refresh_token")) redirect("/");

  return (
    <main className={styles.shell}>
      <aside className={styles.brandPanel}>
        <div className={styles.mosaic} aria-hidden="true">
          {["#3946d6", "#0b8f9e", "#e0561b", "#d12f66", "#2b9a4b", "#c98200", "#7b3fe4", "#566180", "#3946d6"].map(
            (c, i) => (
              <span key={i} style={{ background: c, opacity: i % 2 ? 0.9 : 1 }} />
            )
          )}
        </div>
        <div>
          <div className={styles.logo}>
            <span className={styles.logoMark} />
            Teamboard
          </div>
          <h1>Every team.<br />One clear board.</h1>
          <p>
            Project managers plan the work, teammates move it forward, and the
            owner sees the whole picture.
          </p>
        </div>
        <ul className={styles.points}>
          <li><b>Teams</b> run separate projects</li>
          <li><b>PMs</b> assign work to some or all members</li>
          <li><b>Assignees</b> update status on their board</li>
        </ul>
      </aside>
      <section className={styles.formPanel}>{children}</section>
    </main>
  );
}
