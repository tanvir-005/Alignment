import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { djangoFetch } from "@/lib/django";

export const dynamic = "force-dynamic";

// Send each person to the right home: login, admin overview or their tasks.
export default async function Home() {
  const store = await cookies();
  if (!store.get("access_token") && !store.get("refresh_token")) redirect("/login");

  let destination = "/my-tasks";
  try {
    const response = await djangoFetch("/auth/me/");
    if (response.status === 401) redirect("/login");
    if (response.ok) {
      const me = await response.json();
      if (me.is_admin) destination = "/admin";
    }
  } catch (error) {
    if (error?.digest?.startsWith?.("NEXT_REDIRECT")) throw error;
  }
  redirect(destination);
}
