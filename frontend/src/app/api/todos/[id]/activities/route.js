
import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET(request, { params }) {
  const { id } = await params;
  const searchParams = request.nextUrl.searchParams;
  const query = searchParams.toString();

  try {
    const response = await djangoFetch(
      `/todos/${id}/activities/${query ? `?${query}` : ""}`
    );

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Todo activity proxy error:", error);

    return NextResponse.json(
      { error: "Unable to retrieve task activity." },
      { status: 503 }
    );
  }
}
