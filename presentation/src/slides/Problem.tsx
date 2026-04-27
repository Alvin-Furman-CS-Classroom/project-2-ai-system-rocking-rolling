import type { SlideProps } from "./types";

// Waypoints computed via Python: equidistant (d=80px perpendicular) from the A→B diagonal.
// Diagonal: A(80,290)→B(1080,75). At t=0.25,0.5,0.75 along diagonal, offset ±80px normal.
// Smooth cubic bezier spline via Catmull-Rom (C1-continuous at every waypoint).
// First control adjusted rightward so path clears A's album art before rising.
const WAYPOINTS = [
  { cx: 313, cy: 158 }, // t=0.25, above diagonal
  { cx: 597, cy: 261 }, // t=0.50, below diagonal
  { cx: 813, cy: 51 }, // t=0.75, above diagonal
];

const IMG_R = 42;
const A = { cx: 80, cy: 290 };
const B = { cx: 1080, cy: 75 };
const A_ART = { cx: A.cx, cy: A.cy - 32 - 15 - IMG_R }; // above A (cy=201)
const B_ART = { cx: B.cx, cy: B.cy + 32 + 15 + IMG_R }; // below B (cy=164)

export function Problem({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      <h2 className="slide-title animate-item" style={{ animationDelay: "0s" }}>
        Our Goal: <i>The Perfect Playlist</i>
      </h2>
      <p
        className="slide-subtitle animate-item"
        style={{ animationDelay: "0.1s" }}
      >
        Smooth transitions, a musical journey from start to finish.
      </p>

      {/* Winding path visualization */}
      <div
        className="animate-item"
        style={{
          position: "absolute",
          top: 145,
          left: 60,
          right: 60,
          animationDelay: "0.2s",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <svg width="1160" height="360" viewBox="0 0 1160 360">
          <defs>
            <clipPath id="clip-art-a">
              <rect
                x={A_ART.cx - IMG_R}
                y={A_ART.cy - IMG_R}
                width={IMG_R * 2}
                height={IMG_R * 2}
                rx={10}
              />
            </clipPath>
            <clipPath id="clip-art-b">
              <rect
                x={B_ART.cx - IMG_R}
                y={B_ART.cy - IMG_R}
                width={IMG_R * 2}
                height={IMG_R * 2}
                rx={10}
              />
            </clipPath>
          </defs>

          {/* Album art */}
          <image
            href="/gjwhf.jpg"
            x={A_ART.cx - IMG_R}
            y={A_ART.cy - IMG_R}
            width={IMG_R * 2}
            height={IMG_R * 2}
            clipPath="url(#clip-art-a)"
            preserveAspectRatio="xMidYMid slice"
          />
          <rect
            x={A_ART.cx - IMG_R}
            y={A_ART.cy - IMG_R}
            width={IMG_R * 2}
            height={IMG_R * 2}
            rx={10}
            fill="none"
            stroke="#e0e0e0"
            strokeWidth="1.5"
          />

          <image
            href="/cn.png"
            x={B_ART.cx - IMG_R}
            y={B_ART.cy - IMG_R}
            width={IMG_R * 2}
            height={IMG_R * 2}
            clipPath="url(#clip-art-b)"
            preserveAspectRatio="xMidYMid slice"
          />
          <rect
            x={B_ART.cx - IMG_R}
            y={B_ART.cy - IMG_R}
            width={IMG_R * 2}
            height={IMG_R * 2}
            rx={10}
            fill="none"
            stroke="#e0e0e0"
            strokeWidth="1.5"
          />

          {/* Catmull-Rom cubic spline — 3 equidistant waypoints, bottom-left to top-right */}
          <path
            d="M 80,290 C 200,280 227,163 313,158 C 399,153 514,279 597,261 C 680,243 732,82 813,51 C 894,20 991,67 1080,75"
            stroke="#e0e0e0"
            strokeWidth="2.5"
            strokeDasharray="10,8"
            fill="none"
          />

          {/* Waypoints */}
          {WAYPOINTS.map((wp, i) => (
            <g key={i}>
              <circle
                cx={wp.cx}
                cy={wp.cy}
                r={16}
                fill="#f5f5f5"
                stroke="#e0e0e0"
                strokeWidth="2"
              />
              <circle cx={wp.cx} cy={wp.cy} r={7} fill="#9ca3af" />
            </g>
          ))}

          {/* Track A node */}
          <circle cx={A.cx} cy={A.cy} r={32} fill="#e8590c" />
          <text
            x={A.cx}
            y={A.cy + 7}
            textAnchor="middle"
            fill="white"
            fontWeight="bold"
            fontSize={22}
            fontFamily="Noto Serif, Georgia, serif"
          >
            A
          </text>

          {/* Track B node */}
          <circle cx={B.cx} cy={B.cy} r={32} fill="#1a1a1a" />
          <text
            x={B.cx}
            y={B.cy + 7}
            textAnchor="middle"
            fill="white"
            fontWeight="bold"
            fontSize={22}
            fontFamily="Noto Serif, Georgia, serif"
          >
            B
          </text>
        </svg>
      </div>

      {/* Question at bottom */}
      <div
        className="card card--orange animate-item"
        style={{
          position: "absolute",
          bottom: 60,
          left: 60,
          right: 60,
          animationDelay: "0.35s",
          textAlign: "center",
          padding: "18px 32px",
        }}
      >
        <p
          style={{
            fontSize: 22,
            fontStyle: "italic",
            color: "#e8590c",
            margin: 0,
          }}
        >
          How can we travel from Track A to Track B through a smooth sequence of
          waypoints?
        </p>
      </div>
    </div>
  );
}
