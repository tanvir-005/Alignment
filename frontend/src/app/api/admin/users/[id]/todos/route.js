import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET(_request, { params }) {
  const { id } = await params;
  try {
    const response = await djangoFetch(`/admin/users/${id}/todos/`);
    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Admin user todos proxy error:", error);
    return NextResponse.json(
      { error: "Unable to retrieve user tasks." },
      { status: 503 }
    );
  }
}
