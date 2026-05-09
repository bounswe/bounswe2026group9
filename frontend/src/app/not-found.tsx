import Link from "next/link";

export default function NotFound() {
  return (
    <div className="bg-brand-bg relative flex min-h-screen flex-col overflow-hidden">
      {/* Faint background code */}
      <span className="font-heading text-brand-dark/15 pointer-events-none absolute top-1/2 left-1/2 z-0 -translate-x-1/2 -translate-y-1/2 text-[200px] leading-none font-bold select-none sm:text-[120px] md:text-[200px]">
        404
      </span>

      {/* Logo */}
      <Link
        href="/"
        className="font-heading text-brand-dark absolute top-[72px] left-10 z-10 flex items-center gap-2.5 text-[22px] font-bold no-underline transition-opacity hover:opacity-70 sm:top-16 sm:left-6 sm:text-lg"
      >
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
          <circle cx="14" cy="14" r="13" stroke="currentColor" strokeWidth="2" />
          <path
            d="M14 4C14 4 6 10 6 16a8 8 0 0016 0c0-6-8-12-8-12z"
            fill="currentColor"
            opacity="0.3"
          />
          <circle cx="14" cy="14" r="4" fill="currentColor" />
        </svg>
        Social Event Mapper
      </Link>

      {/* Centered content */}
      <div className="relative z-[2] mx-auto flex max-w-[600px] flex-1 flex-col items-center justify-center px-6 py-20 text-center">
        {/* Magnifying glass icon */}
        <div className="mb-6">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
            <circle cx="34" cy="34" r="22" stroke="#AB886D" strokeWidth="4" fill="none" />
            <line
              x1="50"
              y1="50"
              x2="70"
              y2="70"
              stroke="#AB886D"
              strokeWidth="5"
              strokeLinecap="round"
            />
            <text
              x="34"
              y="42"
              textAnchor="middle"
              fontFamily="Playfair Display, serif"
              fontSize="26"
              fontWeight="700"
              fill="#AB886D"
            >
              ?
            </text>
          </svg>
        </div>

        <h1 className="font-heading text-brand-dark mb-4 text-4xl leading-tight font-bold sm:text-[28px]">
          Page not found
        </h1>
        <p className="text-brand-dark/75 mb-8 max-w-[440px] text-[17px] leading-[1.7]">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/"
            className="bg-brand-dark border-brand-dark inline-flex items-center gap-2 rounded-xl border-2 px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:-translate-y-0.5 hover:border-[#5e4535] hover:bg-[#5e4535] hover:shadow-lg"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path
                d="M10 2L4 8l6 6"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            Back to Home
          </Link>
          <Link
            href="/"
            className="border-brand-dark text-brand-dark hover:bg-brand-dark inline-flex items-center gap-2 rounded-xl border-2 bg-transparent px-7 py-3.5 text-[15px] font-bold transition-all hover:-translate-y-0.5 hover:text-white hover:shadow-lg"
          >
            Browse Events
          </Link>
        </div>
      </div>
    </div>
  );
}
