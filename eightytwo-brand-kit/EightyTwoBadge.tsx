import React, { useId } from "react";

interface EightyTwoBadgeProps {
  size?: number | string;
  speed?: number;
  isStatic?: boolean;
  className?: string;
}

export function EightyTwoBadge({
  size = 200,
  speed = 1,
  isStatic = false,
  className = "",
}: EightyTwoBadgeProps) {
  const rawId = useId();
  // Ensure the ID is valid for SVG (no colons)
  const uid = `eightytwo-badge-${rawId.replace(/:/g, "")}`;

  const outerDur = (22 / speed).toFixed(2);
  const innerDur = (14 / speed).toFixed(2);
  const rimDur = (4 / speed).toFixed(2);
  const centerDur = (4 / speed).toFixed(2);

  const outerStyle = isStatic
    ? {}
    : {
        transformOrigin: "250px 250px",
        animation: `eightytwoRingRotate ${outerDur}s linear infinite`,
      };
  const innerStyle = isStatic
    ? {}
    : {
        transformOrigin: "250px 250px",
        animation: `eightytwoRingRotateRev ${innerDur}s linear infinite`,
      };
  const rimStyle = isStatic
    ? {}
    : { animation: `eightytwoRimPulse ${rimDur}s ease-in-out infinite` };
  const centerTextStyle = isStatic
    ? {}
    : { animation: `eightytwoCenterFade ${centerDur}s ease-in-out infinite` };
  const dotStyle = isStatic
    ? {}
    : { animation: `eightytwoDotGlow ${rimDur}s ease-in-out infinite` };

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 500 500"
      xmlns="http://www.w3.org/2000/svg"
      role="img"
      aria-label="Eighty-Two (82) element badge"
      className={className}
      style={{ display: "block", overflow: "visible" }}
    >
      <title>Eighty-Two (82)</title>

      <defs>
        <radialGradient id={`${uid}-bg`} cx="40%" cy="35%" r="65%">
          <stop offset="0%" stopColor="#141c2e" />
          <stop offset="100%" stopColor="#07090f" />
        </radialGradient>

        <radialGradient id={`${uid}-disk`} cx="38%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#1a2540" />
          <stop offset="100%" stopColor="#0a0f1c" />
        </radialGradient>

        <linearGradient id={`${uid}-num`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f0f4ff" />
          <stop offset="35%" stopColor="#ffffff" />
          <stop offset="100%" stopColor="#8a96b8" />
        </linearGradient>

        <filter
          id={`${uid}-glow`}
          x="-30%"
          y="-30%"
          width="160%"
          height="160%"
        >
          <feGaussianBlur in="SourceGraphic" stdDeviation="8" result="blur" />
          <feColorMatrix
            in="blur"
            type="matrix"
            values="1 0.3 0 0 0   0.2 0.1 0 0 0   0 0 0 0 0   0 0 0 0.6 0"
            result="orange"
          />
          <feMerge>
            <feMergeNode in="orange" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Background */}
      <circle cx="250" cy="250" r="250" fill={`url(#${uid}-bg)`} />

      {/* Outermost guide ring */}
      <circle
        cx="250"
        cy="250"
        r="214"
        fill="none"
        stroke="#0f1826"
        strokeWidth="3"
      />

      {/* Rotating outer ring + cardinal dots */}
      <g style={outerStyle}>
        <circle
          cx="250"
          cy="250"
          r="205"
          fill="none"
          stroke="#1e2e48"
          strokeWidth="2.5"
          strokeDasharray="4 9"
        />
        {/* Cardinal dots — now orange */}
        <circle
          cx="250"
          cy="45"
          r="3.5"
          fill="#ff6b35"
          opacity=".85"
          style={dotStyle}
        />
        <circle
          cx="455"
          cy="250"
          r="3.5"
          fill="#ff6b35"
          opacity=".85"
          style={dotStyle}
        />
        <circle
          cx="250"
          cy="455"
          r="3.5"
          fill="#ff6b35"
          opacity=".85"
          style={dotStyle}
        />
        <circle
          cx="45"
          cy="250"
          r="3.5"
          fill="#ff6b35"
          opacity=".85"
          style={dotStyle}
        />
        {/* Diagonal minor dots */}
        <circle cx="395" cy="99" r="2" fill="#cc4a1a" opacity=".55" />
        <circle cx="395" cy="401" r="2" fill="#cc4a1a" opacity=".55" />
        <circle cx="105" cy="99" r="2" fill="#cc4a1a" opacity=".55" />
        <circle cx="105" cy="401" r="2" fill="#cc4a1a" opacity=".55" />
      </g>

      {/* Counter-rotating inner ring */}
      <g style={innerStyle}>
        <circle
          cx="250"
          cy="250"
          r="172"
          fill="none"
          stroke="#1a2840"
          strokeWidth="1.5"
          strokeDasharray="2 13"
        />
      </g>

      {/* Pulsing rim (double) */}
      <circle
        cx="250"
        cy="250"
        r="184"
        fill="none"
        stroke="#3a2818"
        strokeWidth="3"
        style={rimStyle}
      />
      <circle
        cx="250"
        cy="250"
        r="179"
        fill="none"
        stroke="#ff6b35"
        strokeWidth="2"
        opacity=".35"
        style={rimStyle}
      />

      {/* Main coin disk */}
      <circle cx="250" cy="250" r="156" fill={`url(#${uid}-disk)`} />
      <circle
        cx="250"
        cy="250"
        r="156"
        fill="none"
        stroke="#263040"
        strokeWidth="2"
      />
      <circle
        cx="250"
        cy="250"
        r="149"
        fill="none"
        stroke="#1a2030"
        strokeWidth="1.5"
      />

      {/* Inner arc guides */}
      <path
        d="M 250 94 A 156 156 0 0 1 406 250"
        fill="none"
        stroke="#2a3040"
        strokeWidth="1.5"
      />
      <path
        d="M 250 406 A 156 156 0 0 1 94 250"
        fill="none"
        stroke="#2a3040"
        strokeWidth="1.5"
      />

      {/* Glow bloom behind the number */}
      <circle cx="250" cy="250" r="90" fill="#ff6b35" opacity=".04" />

      {/* PRIMARY number "82" — large, metallic, centered */}
      <text
        x="250"
        y="272"
        fontFamily="'Helvetica Neue', Helvetica, Arial, sans-serif"
        fontSize="172"
        fontWeight="800"
        letterSpacing="-6"
        fill={`url(#${uid}-num)`}
        textAnchor="middle"
        dominantBaseline="middle"
        filter={`url(#${uid}-glow)`}
        style={centerTextStyle}
      >
        82
      </text>

      {/* "EIGHTY-TWO" legend top */}
      <text
        x="250"
        y="176"
        fontFamily="'Helvetica Neue', Helvetica, Arial, sans-serif"
        fontSize="11"
        fontWeight="400"
        letterSpacing="5"
        fill="#3a4a60"
        textAnchor="middle"
      >
        EIGHTY-TWO
      </text>

      {/* Atomic mass bottom */}
      <text
        x="250"
        y="398"
        fontFamily="'Helvetica Neue', Helvetica, Arial, sans-serif"
        fontSize="10"
        fontWeight="300"
        letterSpacing="3"
        fill="#1e2e44"
        textAnchor="middle"
      >
        207.2 u
      </text>

      {/* Flanking rules around mass */}
      <line
        x1="185"
        y1="387"
        x2="215"
        y2="387"
        stroke="#ff6b35"
        strokeWidth="1"
        opacity=".4"
      />
      <line
        x1="285"
        y1="387"
        x2="315"
        y2="387"
        stroke="#ff6b35"
        strokeWidth="1"
        opacity=".4"
      />
    </svg>
  );
}
