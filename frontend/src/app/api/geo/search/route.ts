import { NextResponse } from "next/server";

const BASE = "https://nominatim.openstreetmap.org";
const USER_AGENT = "SocialEventMapper/1.0";
const TIMEOUT_MS = 5000;

// Server-side proxy for Nominatim place suggestions. The browser cannot reach
// Nominatim directly because the upstream service does not return CORS headers.
// Mirrors mobile/data/remote/NominatimClient.kt#suggest.
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const q = searchParams.get("q")?.trim();
  const limit = Math.min(Math.max(parseInt(searchParams.get("limit") ?? "5", 10) || 5, 1), 10);

  if (!q) return NextResponse.json([], { status: 200 });

  const target = `${BASE}/search?q=${encodeURIComponent(q)}&format=json&limit=${limit}&addressdetails=1`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const upstream = await fetch(target, {
      signal: controller.signal,
      headers: { "User-Agent": USER_AGENT, Accept: "application/json" },
    });
    if (!upstream.ok) return NextResponse.json([], { status: 200 });
    const body: unknown = await upstream.json();
    return NextResponse.json(body);
  } catch {
    return NextResponse.json([], { status: 200 });
  } finally {
    clearTimeout(timeoutId);
  }
}
