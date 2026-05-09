import { NextResponse } from "next/server";

const BASE = "https://nominatim.openstreetmap.org";
const USER_AGENT = "SocialEventMapper/1.0";
const TIMEOUT_MS = 5000;

// Server-side proxy for Nominatim reverse-geocoding. Mirrors mobile's
// NominatimClient.reverseGeocode behaviour (returns an empty body on any
// upstream failure so the client treats it as "no address available").
export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const lat = searchParams.get("lat");
  const lng = searchParams.get("lng");

  if (!lat || !lng) return NextResponse.json({ display_name: null }, { status: 200 });

  const target = `${BASE}/reverse?lat=${encodeURIComponent(lat)}&lon=${encodeURIComponent(lng)}&format=json`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const upstream = await fetch(target, {
      signal: controller.signal,
      headers: { "User-Agent": USER_AGENT, Accept: "application/json" },
    });
    if (!upstream.ok) return NextResponse.json({ display_name: null }, { status: 200 });
    const body: unknown = await upstream.json();
    return NextResponse.json(body);
  } catch {
    return NextResponse.json({ display_name: null }, { status: 200 });
  } finally {
    clearTimeout(timeoutId);
  }
}
