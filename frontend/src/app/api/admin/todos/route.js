import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET(request) {
  try {
    const { search } = new URL(request.url);
    const response = await djangoFetch(`/admin/todos/${search}`);
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Admin todo explorer proxy error:", error);
    return NextResponse.json(
      { error: "Unable to retrieve workspace todos." },
      { status: 503 }
    );
  }
}