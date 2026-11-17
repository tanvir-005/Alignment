import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET() {
  try {
    const response = await djangoFetch("/notifications/unread-count/");
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Unread count proxy error:", error);

    return NextResponse.json(
      { error: "Unable to retrieve unread count." },
      { status: 503 }
    );
  }
}