import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import WorkspaceShell from "@/components/layout/WorkspaceShell";

export default async function WorkspaceLayout({ children }) {
  const store = await cookies();
  if (!store.get("access_token") && !store.get("refresh_token")) redirect("/login");
  return <WorkspaceShell>{children}</WorkspaceShell>;
}
