import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

/**
 * One authenticated pass-through to Django for everything except login /
 * register / logout (which have their own routes because they manage cookies).
 * Only whitelisted top-level resources are reachable.
 */
const ALLOWED = new Set(["todos", "teams", "users", "notifications", "admin"]);

async function proxy(request, { params }) {
  const { path } = await params;

  const isMe = path.length === 2 && path[0] === "auth" && path[1] === "me";
  if (!isMe && !ALLOWED.has(path[0])) {
    return NextResponse.json({ error: "Resource not found." }, { status: 404 });
  }

  const { search } = new URL(request.url);
  const target = `/${path.join("/")}/${search}`;

  try {
    const init = { method: request.method };
    if (!["GET", "HEAD"].includes(request.method)) {
      const text = await request.text();
      if (text) {
        init.body = text;
        init.headers = { "Content-Type": "application/json" };
      }
    }

    const response = await djangoFetch(target, init);
    const text = await response.text();

    return new NextResponse(response.status === 204 ? null : text, {
      status: response.status,
      headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" },
    });
  } catch (error) {
    console.error("API proxy error:", error);
    return NextResponse.json(
      { error: "Unable to reach the server. Please try again." },
      { status: 503 }
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PATCH, proxy as PUT, proxy as DELETE };
