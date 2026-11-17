import Link from "next/link";
import styles from "./not-found.module.css";

export default function NotFound() {
  return (
    <main className={styles.page}>
      <div className={styles.content}>
        <p className={styles.eyebrow}>TODO WORKSPACE / 404</p>
        <p className={styles.code}>404</p>
        <h1>Page not found</h1>
        <p className={styles.description}>
          The page you are looking for does not exist or may have been moved.
        </p>
        <Link href="/todos" className={styles.link}>Return to workspace</Link>
      </div>
    </main>
  );
}
