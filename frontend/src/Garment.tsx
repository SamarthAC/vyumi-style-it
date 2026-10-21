import { useId } from "react";
import { palette, type Product } from "./catalog";

/** Original vector artwork. The backend currently supplies placeholder assets. */
export default function Garment({ product }: { product: Product }) {
  const id = useId().replace(/:/g, "");
  const color = palette[product.id]?.color || "#a7b29b";
  const shirt = product.category === "shirt";
  const dress = product.category === "dress";
  const floral = /floral|summer_maxi/.test(product.id);
  const shape = dress
    ? "M119 49 143 40Q160 61 177 40L201 49 190 124 231 287Q160 305 89 287L130 124Z"
    : shirt
      ? "M111 56 141 44 160 54 179 44 209 56 255 99 223 139 202 122 207 264Q160 277 113 264L118 122 97 139 65 99Z"
      : floral
        ? "M118 48 141 43Q160 65 179 43L202 48 195 88 202 254Q160 275 118 254L125 88Z"
        : "M113 58 141 46Q160 64 179 46L207 58 241 105 216 127 198 111 203 259Q160 270 117 259L122 111 104 127 79 105Z";
  return (
    <svg
      viewBox="0 0 320 340"
      role="img"
      aria-label={`Illustration of ${product.name}`}
    >
      <defs>
        <linearGradient id={`${id}shade`} x1="0" x2="1">
          <stop stopColor="#000" stopOpacity=".13" />
          <stop offset=".25" stopColor="#fff" stopOpacity=".14" />
          <stop offset=".65" stopColor="#fff" stopOpacity=".06" />
          <stop offset="1" stopColor="#000" stopOpacity=".17" />
        </linearGradient>
        <pattern
          id={`${id}floral`}
          width="29"
          height="35"
          patternUnits="userSpaceOnUse"
        >
          <path
            d="m9 25 4-14m-1 5-6-4m7 8 7-5"
            stroke="#697b5e"
            strokeWidth="1.3"
          />
          <path
            d="M11 10q-8-9-8 0 2 7 8 0m0 0q9-8 9 0-2 8-9 0"
            fill="#f6e5cf"
          />
        </pattern>
        <pattern
          id={`${id}rib`}
          width="5"
          height="6"
          patternUnits="userSpaceOnUse"
        >
          <path d="M1 0v6" stroke="#fff" strokeOpacity=".13" />
        </pattern>
        <filter id={`${id}shadow`} x="-40%" y="-20%" width="180%" height="160%">
          <feDropShadow dx="2" dy="15" stdDeviation="9" floodOpacity=".13" />
        </filter>
      </defs>
      <ellipse cx="160" cy="305" rx="79" ry="7" fill="#000" opacity=".045" />
      <g filter={`url(#${id}shadow)`}>
        <path
          d={shape}
          fill={color}
          stroke="#000"
          strokeOpacity=".12"
          strokeWidth="1"
          strokeLinejoin="round"
        />
        {floral && <path d={shape} fill={`url(#${id}floral)`} opacity=".8" />}
        {!shirt && !floral && <path d={shape} fill={`url(#${id}rib)`} />}
        <path d={shape} fill={`url(#${id}shade)`} />
        {shirt ? (
          <>
            <path
              d="m141 44-9 26 18 20 10-36 10 36 18-20-9-26M160 55v216M118 122l5-33m79 33-5-33"
              fill="none"
              stroke="#000"
              strokeOpacity=".19"
              strokeWidth="1.2"
            />
            <path
              d="M177 109h20v27q-10 9-20 0Z"
              fill="none"
              stroke="#000"
              strokeOpacity=".14"
            />
            {[99, 128, 157, 186, 215, 244].map((y) => (
              <circle
                key={y}
                cx="165"
                cy={y}
                r="1.8"
                fill="#000"
                opacity=".3"
              />
            ))}
            <path
              d="m70 104 30 31m120 0 30-31M119 256q41 12 82 0"
              stroke="#fff"
              strokeOpacity=".3"
              fill="none"
            />
          </>
        ) : (
          <>
            <path
              d={
                dress
                  ? "M143 40q17 29 34 0M130 124q30 10 60 0M131 145l-20 139m42-132-3 139m28-139 20 135"
                  : "M141 46q19 31 38 0M123 250q37 12 75 0"
              }
              fill="none"
              stroke="#000"
              strokeOpacity=".14"
              strokeWidth="1.5"
            />
            {dress && floral && (
              <path
                d="M113 207q47 13 94 0M101 254q59 14 118 0"
                fill="none"
                stroke="#fff"
                strokeOpacity=".4"
              />
            )}
          </>
        )}
      </g>
    </svg>
  );
}
