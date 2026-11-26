import { NextResponse } from "next/server";

const API_URL = process.env.DJANGO_API_URL;

export async function POST(request) {
  try {
    const body = await request.json();

    const response = await fetch(`${API_URL}/auth/register/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
      cache: "no-store",
    });

    const data = await response.json();
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Register proxy error:", error);
    return NextResponse.json(
      { error: "Unable to create the account right now." },
      { status: 503 }
    );
  }
}
