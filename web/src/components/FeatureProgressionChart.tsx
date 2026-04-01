import type { TrackInfo } from "../types";

const MOOD_COLORS: Record<string, string> = {
  calm: "#60a5fa",
  energized: "#fb923c",
  happy: "#facc15",
  sad: "#a78bfa",
  intense: "#f87171",
  chill: "#2dd4bf",
};

interface FeatureProgressionChartProps {
  tracks: TrackInfo[];
  compact?: boolean;
}

/**
 * Compact: sparkline bars (BPM + energy) shown inline.
 * Full: SVG line chart with labeled axes, BPM and energy lines, mood pills.
 */
export function FeatureProgressionChart({
  tracks,
  compact = true,
}: FeatureProgressionChartProps) {
  if (tracks.length === 0) return null;

  const bpms = tracks.map((t) => t.bpm ?? 0);
  const energies = tracks.map((t) => t.energy ?? 0);

  const maxBpm = Math.max(...bpms, 1);
  const minBpm = Math.min(...bpms.filter((b) => b > 0), maxBpm);
  const bpmRange = maxBpm - minBpm || 1;

  if (compact) {
    return <CompactChart tracks={tracks} bpms={bpms} energies={energies} minBpm={minBpm} bpmRange={bpmRange} />;
  }

  return <FullChart tracks={tracks} bpms={bpms} energies={energies} minBpm={minBpm} bpmRange={bpmRange} />;
}

interface ChartProps {
  tracks: TrackInfo[];
  bpms: number[];
  energies: number[];
  minBpm: number;
  bpmRange: number;
}

function CompactChart({ tracks, bpms, energies, minBpm, bpmRange }: ChartProps) {
  return (
    <div>
      <div className="flex items-end gap-1.5 h-12">
        {tracks.map((_track, i) => {
          const bpmNorm = bpms[i] > 0 ? (bpms[i] - minBpm) / bpmRange : 0;
          const energyNorm = energies[i];
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5 h-full justify-end">
              <div className="flex items-end gap-0.5 w-full h-10">
                {/* BPM bar */}
                <div
                  className="flex-1 rounded-t bg-indigo-500/70"
                  style={{ height: `${Math.max(4, bpmNorm * 100)}%` }}
                  title={`BPM: ${bpms[i] > 0 ? Math.round(bpms[i]) : "—"}`}
                />
                {/* Energy bar */}
                <div
                  className="flex-1 rounded-t bg-emerald-500/70"
                  style={{ height: `${Math.max(4, energyNorm * 100)}%` }}
                  title={`Energy: ${energies[i] > 0 ? (energies[i] * 100).toFixed(0) + "%" : "—"}`}
                />
              </div>
              <span className="text-gray-600 text-[9px] leading-none">{i + 1}</span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-3 mt-1.5">
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm bg-indigo-500/70" />
          BPM
        </span>
        <span className="flex items-center gap-1 text-xs text-gray-500">
          <span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500/70" />
          Energy
        </span>
      </div>
    </div>
  );
}

function FullChart({ tracks, bpms, energies, minBpm, bpmRange }: ChartProps) {
  const W = 560;
  const H = 220;
  const PAD = { top: 20, right: 20, bottom: 56, left: 44 };
  const innerW = W - PAD.left - PAD.right;
  const innerH = H - PAD.top - PAD.bottom;
  const n = tracks.length;

  const xPos = (i: number) => PAD.left + (i / Math.max(n - 1, 1)) * innerW;

  // Normalize BPM to [0,1] within the observed range
  const normBpm = (bpm: number) =>
    bpm > 0 ? (bpm - minBpm) / bpmRange : 0;

  const yBpm = (bpm: number) =>
    PAD.top + (1 - normBpm(bpm)) * innerH;

  const yEnergy = (e: number) =>
    PAD.top + (1 - e) * innerH;

  const bpmPoints = tracks
    .map((_, i) => `${xPos(i).toFixed(1)},${yBpm(bpms[i]).toFixed(1)}`)
    .join(" ");

  const energyPoints = tracks
    .map((_, i) => `${xPos(i).toFixed(1)},${yEnergy(energies[i]).toFixed(1)}`)
    .join(" ");

  return (
    <div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full"
        aria-label="Feature progression"
      >
        {/* Grid lines */}
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = PAD.top + (1 - t) * innerH;
          return (
            <line
              key={t}
              x1={PAD.left}
              y1={y}
              x2={PAD.left + innerW}
              y2={y}
              stroke="#374151"
              strokeWidth="1"
            />
          );
        })}

        {/* BPM line */}
        <polyline
          points={bpmPoints}
          fill="none"
          stroke="#818cf8"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Energy line */}
        <polyline
          points={energyPoints}
          fill="none"
          stroke="#34d399"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Dots + track labels */}
        {tracks.map((track, i) => {
          const x = xPos(i);
          const moodColor = track.mood_label
            ? MOOD_COLORS[track.mood_label] ?? "#9ca3af"
            : "#9ca3af";
          const name =
            track.title
              ? track.title.length > 12
                ? track.title.slice(0, 11) + "…"
                : track.title
              : `#${i + 1}`;
          return (
            <g key={i}>
              {/* BPM dot */}
              <circle
                cx={x}
                cy={yBpm(bpms[i])}
                r="3"
                fill="#818cf8"
              />
              {/* Energy dot */}
              <circle
                cx={x}
                cy={yEnergy(energies[i])}
                r="3"
                fill="#34d399"
              />
              {/* Mood pill */}
              {track.mood_label && (
                <rect
                  x={x - 16}
                  y={H - PAD.bottom + 8}
                  width="32"
                  height="12"
                  rx="6"
                  fill={moodColor}
                  opacity="0.8"
                />
              )}
              {track.mood_label && (
                <text
                  x={x}
                  y={H - PAD.bottom + 17}
                  textAnchor="middle"
                  fontSize="7"
                  fill="#111827"
                  fontWeight="600"
                >
                  {track.mood_label}
                </text>
              )}
              {/* Track name */}
              <text
                x={x}
                y={H - PAD.bottom + 26}
                textAnchor="middle"
                fontSize="8"
                fill="#9ca3af"
              >
                {name}
              </text>
            </g>
          );
        })}

        {/* Y-axis label */}
        <text
          x={PAD.left - 8}
          y={PAD.top + innerH / 2}
          textAnchor="middle"
          fontSize="9"
          fill="#6b7280"
          transform={`rotate(-90, ${PAD.left - 8}, ${PAD.top + innerH / 2})`}
        >
          Normalized
        </text>
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-4 mt-1 justify-center">
        <span className="flex items-center gap-1.5 text-sm text-gray-400">
          <svg width="20" height="4">
            <line x1="0" y1="2" x2="20" y2="2" stroke="#818cf8" strokeWidth="2" />
          </svg>
          BPM
        </span>
        <span className="flex items-center gap-1.5 text-sm text-gray-400">
          <svg width="20" height="4">
            <line x1="0" y1="2" x2="20" y2="2" stroke="#34d399" strokeWidth="2" />
          </svg>
          Energy
        </span>
      </div>
    </div>
  );
}
