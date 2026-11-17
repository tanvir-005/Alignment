import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET(request) {
  try {
    const { search } = new URL(request.url);

    const response = await djangoFetch(`/todos/${search}`);
    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Todo list proxy error:", error);

    return NextResponse.json(
      { error: "Unable to retrieve todos." },
      { status: 503 }
    );
  }
}

export async function POST(request) {
  try {
    const body = await request.json();

    const response = await djangoFetch("/todos/", {
      method: "POST",
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
    console.error("Todo creation proxy error:", error);

    return NextResponse.json(
      { error: "Unable to create todo." },
      { status: 503 }
    );
  }
}