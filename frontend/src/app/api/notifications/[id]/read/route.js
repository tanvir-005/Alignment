import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function PATCH(request, { params }) {
  const { id } = await params;

  try {
    // const response = await djangoFetch(`/notifications/${id}/read/`);
    const response = await djangoFetch(`/notifications/${id}/read/`, { method: "PATCH", });
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Mark notification read proxy error:", error);

    return NextResponse.json(
      { error: "Unable to mark notification as read." },
      { status: 503 }
    );
  }
}