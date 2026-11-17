import { NextResponse } from "next/server";
import { djangoFetch } from "@/lib/django";

export async function GET(request, { params }) {
  const { id } = await params;

  try {
    const response = await djangoFetch(`/todos/${id}/`);
    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Todo detail proxy error:", error);

    return NextResponse.json(
      { error: "Unable to retrieve todo." },
      { status: 503 }
    );
  }
}

export async function PATCH(request, { params }) {
  const { id } = await params;

  try {
    const body = await request.json();

    const response = await djangoFetch(`/todos/${id}/`, {
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
    console.error("Todo update proxy error:", error);

    return NextResponse.json(
      { error: "Unable to update todo." },
      { status: 503 }
    );
  }
}

export async function DELETE(request, { params }) {
  const { id } = await params;

  try {
    const response = await djangoFetch(`/todos/${id}/`, {
      method: "DELETE",
    });

    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    const data = await response.json();

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch (error) {
    console.error("Todo deletion proxy error:", error);

    return NextResponse.json(
      { error: "Unable to delete todo." },
      { status: 503 }
    );
  }
}