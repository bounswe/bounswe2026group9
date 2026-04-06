import Link from "next/link";

export default function NotFound() {
  return (
    <div className="bg-brand-bg min-h-screen relative overflow-hidden flex flex-col">
      {/* Faint background code */}
      <span className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 font-heading text-[200px] sm:text-[120px] md:text-[200px] font-bold text-brand-dark/15 select-none pointer-events-none leading-none z-0">
        404
      </span>

      {/* Logo */}
      <Link
        href="/"
        className="absolute top-[72px] left-10 z-10 font-heading text-[22px] font-bold text-brand-dark flex items-center gap-2.5 no-underline hover:opacity-70 transition-opacity sm:top-16 sm:left-6 sm:text-lg"
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
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-20 text-center relative z-[2] max-w-[600px] mx-auto">
        {/* Magnifying glass icon */}
        <div className="mb-6">
          <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
            <circle cx="34" cy="34" r="22" stroke="#AB886D" strokeWidth="4" fill="none" />
            <line x1="50" y1="50" x2="70" y2="70" stroke="#AB886D" strokeWidth="5" strokeLinecap="round" />
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

        <h1 className="font-heading text-4xl sm:text-[28px] font-bold text-brand-dark mb-4 leading-tight">
          Page not found
        </h1>
        <p className="text-[17px] leading-[1.7] text-brand-dark/75 max-w-[440px] mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>

        <div className="flex gap-4 flex-wrap justify-center">
          <Link
            href="/"
            className="inline-flex items-center gap-2 rounded-xl bg-brand-dark border-2 border-brand-dark px-7 py-3.5 text-[15px] font-bold text-white transition-all hover:bg-[#5e4535] hover:border-[#5e4535] hover:-translate-y-0.5 hover:shadow-lg"
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
            className="inline-flex items-center gap-2 rounded-xl bg-transparent border-2 border-brand-dark px-7 py-3.5 text-[15px] font-bold text-brand-dark transition-all hover:bg-brand-dark hover:text-white hover:-translate-y-0.5 hover:shadow-lg"
          >
            Browse Events
          </Link>
        </div>
      </div>
    </div>
  );
}
