import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function POST() {
  try {
    const response = await djangoFetch("/notifications/read-all/", {
      method: "POST",
    });
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Mark all notifications read proxy error:", error);

    return NextResponse.json(
      { error: "Unable to mark notifications as read." },
      { status: 503 }
    );
  }
}