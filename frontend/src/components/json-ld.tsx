// Renders a Schema.org / JSON-LD 1.1 block as <script type="application/ld+json">.
// Issue #243.
//
// Next.js renders this script element as-is in the HTML stream; for client
// components it lands in <body>, which crawlers still pick up. We use
// dangerouslySetInnerHTML because JSON-LD must be raw text, not React
// children (React would escape angle brackets and break the JSON parser).

interface JsonLdProps {
  data: Record<string, unknown> | Record<string, unknown>[];
}

export function JsonLd({ data }: JsonLdProps) {
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}
