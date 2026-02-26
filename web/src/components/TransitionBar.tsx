import type { TransitionInfo, CompareComponents } from "../types";
import { scoreColor } from "../utils";
import { COMPONENT_LABELS } from "./ComponentBar";

interface TransitionBarProps {
  transition: TransitionInfo;
  index: number;
}

export function TransitionBar({ transition, index }: TransitionBarProps) {
  return (
    <div className="rounded-lg border border-gray-800 bg-gray-900/50 p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-gray-300">
          Transition {index + 1}
        </span>
        <span
          className={`rounded-full px-2 py-0.5 text-xs font-medium ${
            transition.is_compatible
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {Math.round(transition.probability * 100)}% compatible
        </span>
      </div>
      <div className="space-y-2">
        {(
          Object.entries(COMPONENT_LABELS) as [
            keyof CompareComponents,
            string,
          ][]
        ).map(([key, label]) => (
          <div key={key} className="flex items-center gap-2">
            <span className="w-16 text-xs text-gray-500 text-right shrink-0">
              {label}
            </span>
            <div className="flex-1 h-2 rounded-full bg-gray-800 overflow-hidden">
              <div
                className={`h-full rounded-full ${scoreColor(transition.components[key])}`}
                style={{ width: `${Math.round(transition.components[key] * 100)}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {transition.violations.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {transition.violations.map((v) => (
            <span
              key={v}
              className="text-xs text-red-400 bg-red-500/10 px-2 py-0.5 rounded"
            >
              {v}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
