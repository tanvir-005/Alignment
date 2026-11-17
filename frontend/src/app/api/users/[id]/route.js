import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function PATCH(request, { params }) {
  const { id } = await params;

  try {
    const body = await request.json();

    const response = await djangoFetch(`/users/${id}/`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("User update proxy error:", error);

    return NextResponse.json(
      { error: "Unable to update user." },
      { status: 503 }
    );
  }
}