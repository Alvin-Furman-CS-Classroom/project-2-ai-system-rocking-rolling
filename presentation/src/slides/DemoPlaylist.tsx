import type { DemoSlideProps, PlaylistTrack, Transition } from "./demo-types";
import { T } from "../theme";

export function DemoPlaylist({ isActive, demoState }: DemoSlideProps) {
  const { playlist } = demoState;

  if (!playlist) {
    return (
      <div className={`slide ${isActive ? "active" : ""}`}>
        <h2 className="slide-title">Your Playlist</h2>
        <p className="slide-subtitle">No playlist generated yet</p>
      </div>
    );
  }

  const avgPct = Math.round(playlist.average_compatibility * 100);

  return (
    <div className={`slide ${isActive ? "active" : ""}`}>
      {/* Header */}
      <h2 className="slide-title">Your Playlist</h2>

      {/* Stat pills */}
      <div
        style={{
          position: "absolute",
          top: 62,
          right: T.MARGIN,
          display: "flex",
          gap: 10,
        }}
      >
        <StatPill label="Avg compatibility" value={`${avgPct}%`} />
        <StatPill label="Tracks" value={String(playlist.tracks.length)} />
      </div>

      {/* Body: left track list, right chart + constraints */}
      <div
        style={{
          position: "absolute",
          top: 108,
          left: T.MARGIN,
          right: T.MARGIN,
          bottom: 40,
          display: "flex",
          gap: 24,
        }}
      >
        {/* Left: track list */}
        <div
          style={{
            width: 590,
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          {playlist.tracks.slice(0, 7).map((track, i) => (
            <TrackRow key={track.mbid} track={track} index={i} />
          ))}
        </div>

        {/* Right: chart + constraints */}
        <div
          style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}
        >
          {/* Compatibility arc */}
          <div
            className="card"
            style={{ padding: "14px 16px", flex: "0 0 auto" }}
          >
            <p
              style={{
                fontSize: 12,
                color: T.MUTED,
                fontStyle: "italic",
                marginBottom: 8,
              }}
            >
              Transition compatibility
            </p>
            <CompatibilityArc transitions={playlist.transitions} />
          </div>

          {/* Constraints */}
          <div style={{ flex: 1, overflow: "hidden" }}>
            <p
              style={{
                fontSize: 12,
                color: T.MUTED,
                fontStyle: "italic",
                marginBottom: 8,
              }}
            >
              Constraints applied
            </p>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 8,
              }}
            >
              {playlist.constraints.map((c) => (
                <div
                  key={c.name}
                  className="card"
                  style={{ padding: "10px 14px" }}
                >
                  <div
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      marginBottom: 6,
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: "bold" }}>
                      {formatConstraintName(c.name)}
                    </span>
                    <span
                      style={{
                        fontSize: 14,
                        fontWeight: "bold",
                        color: c.satisfied ? T.ORANGE : "#ef4444",
                      }}
                    >
                      {c.satisfied ? "✓" : "✗"}
                    </span>
                  </div>
                  <div className="progress-track">
                    <div
                      className="progress-fill"
                      style={{ width: `${Math.round(c.score * 100)}%` }}
                    />
                  </div>
                  <p
                    style={{
                      fontSize: 11,
                      color: T.MUTED,
                      marginTop: 4,
                      textAlign: "right",
                    }}
                  >
                    {Math.round(c.score * 100)}%
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Summary */}
          {playlist.summary && (
            <p
              style={{
                fontSize: 13,
                color: T.MUTED,
                fontStyle: "italic",
                lineHeight: 1.5,
                borderTop: `1px solid ${T.BORDER}`,
                paddingTop: 10,
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }}
            >
              {playlist.summary}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatPill({ label, value }: { label: string; value: string }) {
  return (
    <div
      style={{
        padding: "4px 14px",
        borderRadius: 20,
        border: `1.5px solid ${T.ORANGE}`,
        background: T.ORANGE_L,
        display: "flex",
        gap: 6,
        alignItems: "baseline",
      }}
    >
      <span style={{ fontSize: 12, color: T.MUTED }}>{label}</span>
      <span style={{ fontSize: 15, fontWeight: "bold", color: T.ORANGE }}>
        {value}
      </span>
    </div>
  );
}

function TrackRow({ track, index }: { track: PlaylistTrack; index: number }) {
  return (
    <div
      className="animate-item"
      style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "8px 12px",
        borderRadius: 5,
        background: index % 2 === 0 ? T.SURFACE : T.BG,
        border: `0.5px solid ${T.BORDER}`,
        animationDelay: `${index * 0.07}s`,
      }}
    >
      {/* Position */}
      <span
        style={{
          width: 24,
          textAlign: "center",
          fontWeight: "bold",
          color: T.ORANGE,
          fontSize: 14,
          flexShrink: 0,
        }}
      >
        {track.position}
      </span>

      {/* Title + artist */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <p
          style={{
            fontSize: 14,
            fontWeight: "bold",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {track.title ?? "Unknown"}
        </p>
        <p style={{ fontSize: 12, color: T.MUTED }}>{track.artist ?? ""}</p>
      </div>

      {/* Key */}
      {track.key && (
        <span
          style={{ fontSize: 12, color: T.MUTED, flexShrink: 0, width: 48 }}
        >
          {track.key} {track.scale ? track.scale[0].toUpperCase() : ""}
        </span>
      )}

      {/* BPM */}
      {track.bpm && (
        <span
          style={{
            fontSize: 12,
            color: T.MUTED,
            flexShrink: 0,
            width: 54,
            textAlign: "right",
          }}
        >
          {track.bpm.toFixed(0)} BPM
        </span>
      )}
    </div>
  );
}

function CompatibilityArc({ transitions }: { transitions: Transition[] }) {
  if (transitions.length === 0) return null;

  const W = 520,
    H = 120;
  const PAD = { top: 10, right: 16, bottom: 24, left: 36 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top - PAD.bottom;

  const n = transitions.length;
  const xScale = (i: number) => PAD.left + (i / Math.max(n - 1, 1)) * chartW;
  const yScale = (v: number) => PAD.top + (1 - v) * chartH;

  const points = transitions.map((t, i) => ({
    x: xScale(i),
    y: yScale(t.probability),
    p: t.probability,
  }));
  const polyline = points.map((p) => `${p.x},${p.y}`).join(" ");

  return (
    <svg width={W} height={H} style={{ display: "block" }}>
      {/* Grid lines */}
      {[0, 0.5, 1].map((v) => (
        <line
          key={v}
          x1={PAD.left}
          y1={yScale(v)}
          x2={PAD.left + chartW}
          y2={yScale(v)}
          stroke={T.BORDER}
          strokeWidth={1}
        />
      ))}

      {/* Y-axis labels */}
      {[0, 0.5, 1].map((v) => (
        <text
          key={v}
          x={PAD.left - 6}
          y={yScale(v) + 4}
          textAnchor="end"
          fontSize={10}
          fill={T.MUTED}
        >
          {Math.round(v * 100)}%
        </text>
      ))}

      {/* X-axis labels */}
      {points.map((p, i) => (
        <text
          key={i}
          x={p.x}
          y={H - 4}
          textAnchor="middle"
          fontSize={10}
          fill={T.MUTED}
        >
          {i + 1}→{i + 2}
        </text>
      ))}

      {/* Line */}
      <polyline
        points={polyline}
        fill="none"
        stroke={T.ORANGE}
        strokeWidth={2.5}
        strokeLinejoin="round"
      />

      {/* Dots */}
      {points.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={5} fill={T.ORANGE} />
      ))}

      {/* Probability labels above dots */}
      {points.map((p, i) => (
        <text
          key={i}
          x={p.x}
          y={p.y - 9}
          textAnchor="middle"
          fontSize={10}
          fontWeight="bold"
          fill={T.ORANGE_D}
        >
          {Math.round(p.p * 100)}%
        </text>
      ))}
    </svg>
  );
}

function formatConstraintName(name: string): string {
  // "NoRepeatArtists" → "No Repeat Artists"
  return name.replace(/([A-Z])/g, " $1").trim();
}
