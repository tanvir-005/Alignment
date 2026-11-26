import "./globals.css";

export const metadata = {
  title: "Teamboard",
  description: "Team task management for organisations: teams, project managers and assignees.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
