import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET() {
  try {
    const response = await djangoFetch("/teams/");
    const data = await response.json();

    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Teams proxy error:", error);

    return NextResponse.json(
      { error: "Unable to retrieve teams." },
      { status: 503 }
    );
  }
}