// Mirrors mobile/data/remote/NominatimClient.kt — the same OpenStreetMap-hosted
// Nominatim service drives place autocomplete and reverse geocoding for both
// platforms. Browser calls go through the local /api/geo/* route handlers
// because Nominatim does not return CORS headers and forbids browser-set
// User-Agent. The proxy adds the required identifying header server-side.

export interface NominatimResult {
  displayName: string;
  shortName: string;
  lat: number;
  lng: number;
}

interface NominatimAddress {
  amenity?: string;
  building?: string;
  shop?: string;
  tourism?: string;
  neighbourhood?: string;
  suburb?: string;
  quarter?: string;
  city?: string;
  town?: string;
  village?: string;
}

interface NominatimSearchEntry {
  display_name?: string;
  lat?: string;
  lon?: string;
  address?: NominatimAddress;
}

function pickFirst(...values: (string | undefined)[]): string | undefined {
  for (const value of values) {
    if (value?.trim()) return value.trim();
  }
  return undefined;
}

function buildShortName(entry: NominatimSearchEntry): string {
  const addr = entry.address ?? {};
  const venue = pickFirst(addr.amenity, addr.building, addr.shop, addr.tourism);
  const area = pickFirst(addr.neighbourhood, addr.suburb, addr.quarter);
  const city = pickFirst(addr.city, addr.town, addr.village);
  const parts = [venue, area, city].filter((part): part is string => !!part).slice(0, 2);
  if (parts.length > 0) return parts.join(", ");
  return entry.display_name?.split(",")[0]?.trim() ?? "";
}

/** Search suggestions: text → up to {limit} results with coordinates. */
export async function suggestPlaces(
  query: string,
  limit = 5,
  signal?: AbortSignal,
): Promise<NominatimResult[]> {
  const trimmed = query.trim();
  if (!trimmed) return [];
  try {
    const url = `/api/geo/search?q=${encodeURIComponent(trimmed)}&limit=${limit}`;
    const res = await fetch(url, { signal });
    if (!res.ok) return [];
    const entries = (await res.json()) as NominatimSearchEntry[];
    return entries
      .map((entry) => {
        const display = entry.display_name?.trim();
        const lat = entry.lat ? parseFloat(entry.lat) : NaN;
        const lng = entry.lon ? parseFloat(entry.lon) : NaN;
        if (!display || Number.isNaN(lat) || Number.isNaN(lng)) return null;
        const shortName = buildShortName(entry).trim();
        const fallback = display.split(",")[0]?.trim() ?? display;
        return {
          displayName: display,
          shortName: shortName.length > 0 ? shortName : fallback,
          lat,
          lng,
        } satisfies NominatimResult;
      })
      .filter((entry): entry is NominatimResult => entry !== null);
  } catch {
    return [];
  }
}

/** Reverse geocode: (lat, lng) → human-readable address (max 100 chars, first 3 comma-separated parts). */
export async function reverseGeocode(
  lat: number,
  lng: number,
  signal?: AbortSignal,
): Promise<string | null> {
  try {
    const url = `/api/geo/reverse?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`;
    const res = await fetch(url, { signal });
    if (!res.ok) return null;
    const json = (await res.json()) as { display_name?: string | null };
    const display = json.display_name?.trim();
    if (!display) return null;
    const trimmed = display.split(",").slice(0, 3).join(",").trim();
    return trimmed.length > 100 ? trimmed.slice(0, 100) : trimmed;
  } catch {
    return null;
  }
}
