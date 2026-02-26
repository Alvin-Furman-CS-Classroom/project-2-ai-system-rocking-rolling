import type { CompareComponents } from "../types";
import { scoreColor } from "../utils";

const COMPONENT_LABELS: Record<keyof CompareComponents, string> = {
  key: "Key",
  tempo: "Tempo",
  energy: "Energy",
  loudness: "Loudness",
  mood: "Mood",
  timbre: "Timbre",
  genre: "Genre",
};

interface ComponentBarProps {
  label: string;
  value: number;
}

export function ComponentBar({ label, value }: ComponentBarProps) {
  return (
    <div className="flex items-center gap-3">
      <span className="w-20 text-sm text-gray-400 text-right shrink-0">
        {label}
      </span>
      <div className="flex-1 h-3 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ${scoreColor(value)}`}
          style={{ width: `${Math.round(value * 100)}%` }}
        />
      </div>
      <span className="w-12 text-sm text-gray-300 tabular-nums">
        {Math.round(value * 100)}%
      </span>
    </div>
  );
}

export { COMPONENT_LABELS };
