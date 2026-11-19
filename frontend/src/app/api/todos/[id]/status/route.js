import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function PATCH(request, { params }) {
  const { id } = await params;

  try {
    const body = await request.json();

    const response = await djangoFetch(`/todos/${id}/status/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Todo status update proxy error:", error);

    return NextResponse.json(
      { error: "Unable to update task status." },
      { status: 503 }
    );
  }
}