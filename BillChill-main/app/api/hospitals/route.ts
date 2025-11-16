import { NextResponse } from "next/server";

// Proxy POST requests from the Next.js app to the Flask backend.
// Configure the Flask base URL via env var FLASK_BASE_URL (defaults to local dev).
const FLASK_BASE_URL = process.env.FLASK_BASE_URL || "http://127.0.0.1:5000";

export const runtime = "nodejs"; // ensure Node runtime for server-side fetch

export async function POST(req: Request) {
  let payload: any;
  try {
    payload = await req.json();
  } catch (e) {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const { lat, lon, condition } = payload || {};
  if (lat === undefined || lon === undefined) {
    return NextResponse.json({ error: "lat and lon are required" }, { status: 400 });
  }
  if (!condition || typeof condition !== "string" || !condition.trim()) {
    return NextResponse.json({ error: "condition is required" }, { status: 400 });
  }

  try {
    const resp = await fetch(`${FLASK_BASE_URL}/api/hospitals`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ lat, lon, condition }),
      // A short timeout pattern via AbortController
      signal: AbortSignal.timeout ? AbortSignal.timeout(45000) : undefined as any,
    });

    const text = await resp.text();
    let data: any;
    try {
      data = JSON.parse(text);
    } catch {
      data = { error: "Non-JSON response from backend", raw: text?.slice(0, 600) };
    }

    return NextResponse.json(data, { status: resp.status });
  } catch (err: any) {
    return NextResponse.json(
      { error: `Failed to reach backend: ${err?.message || String(err)}` },
      { status: 502 }
    );
  }
}
