import { useState } from "react";
import type { PlaylistResponse } from "../types";
import { FeatureModal } from "./FeatureModal";
import { FeatureProgressionChart } from "./FeatureProgressionChart";
import { TransitionBar } from "./TransitionBar";

interface PlaylistResultsProps {
  result: PlaylistResponse;
}

export function PlaylistResults({ result }: PlaylistResultsProps) {
  const [modalOpen, setModalOpen] = useState(false);

  const hasFeatureData = result.tracks.some(
    (t) => t.energy != null || t.mood_label != null
  );

  return (
    <div className="mt-10 rounded-xl border border-gray-800 bg-gray-900 p-8">
      <div className="text-center mb-8">
        <p className="text-sm text-gray-400 mb-1">Playlist Generated</p>
        <p className="text-4xl font-bold">
          {result.actual_length}{" "}
          <span className="text-lg text-gray-500">tracks</span>
        </p>
        <div className="mt-2 flex items-center justify-center gap-4 text-sm text-gray-500">
          <span>Total Cost: {result.total_cost.toFixed(3)}</span>
          <span>•</span>
          <span>
            Avg Compatibility: {Math.round(result.average_compatibility * 100)}%
          </span>
        </div>
      </div>

      <div className="space-y-4 mb-8">
        <h3 className="text-sm font-medium text-gray-300">Track List</h3>
        {result.tracks.map((track, i) => (
          <div
            key={track.mbid}
            className="flex items-center gap-4 rounded-lg border border-gray-800 bg-gray-900/50 p-4"
          >
            <span className="w-6 text-center text-sm font-medium text-gray-500">
              {i + 1}
            </span>
            <div className="min-w-0 flex-1">
              <p className="font-medium text-white truncate">
                {track.title ?? "Unknown Title"}
              </p>
              <p className="text-sm text-gray-400 truncate">
                {track.artist ?? "Unknown Artist"}
              </p>
            </div>
            <div className="flex items-center gap-3 text-xs text-gray-500 shrink-0">
              {track.bpm && (
                <span className="tabular-nums">{track.bpm} BPM</span>
              )}
              {track.key && (
                <span className="tabular-nums">
                  {track.key} {track.scale ?? ""}
                </span>
              )}
              {track.mood_label && (
                <span className="rounded-full bg-gray-700 px-2 py-0.5 text-gray-300 capitalize">
                  {track.mood_label}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Feature progression chart (compact inline) */}
      {hasFeatureData && (
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-800/50 p-4">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-gray-300">
              Feature Progression
            </h3>
            <button
              onClick={() => setModalOpen(true)}
              className="text-xs text-indigo-400 hover:text-indigo-300 transition cursor-pointer"
            >
              View full visualization →
            </button>
          </div>
          <FeatureProgressionChart tracks={result.tracks} compact={true} />
        </div>
      )}

      {result.summary && (
        <div className="mb-8 rounded-lg border border-gray-700 bg-gray-800/50 p-4">
          <h3 className="text-sm font-medium text-gray-300 mb-2">Summary</h3>
          <p className="text-sm text-gray-400">{result.summary}</p>
        </div>
      )}

      <div className="space-y-3 mb-8">
        <h3 className="text-sm font-medium text-gray-300">Transitions</h3>
        {result.transitions.map((transition, i) => (
          <TransitionBar key={i} transition={transition} index={i} />
        ))}
      </div>

      {result.constraints && result.constraints.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-300">Constraints</h3>
          {result.constraints.map((c) => (
            <div
              key={c.name}
              className="flex items-center justify-between rounded-lg border border-gray-800 bg-gray-900/50 px-4 py-2"
            >
              <span className="text-sm text-gray-300">{c.name}</span>
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-500 tabular-nums">
                  {Math.round(c.score * 100)}%
                </span>
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                    c.satisfied
                      ? "bg-green-900/50 text-green-400"
                      : "bg-red-900/50 text-red-400"
                  }`}
                >
                  {c.satisfied ? "Pass" : "Fail"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      <FeatureModal
        tracks={result.tracks}
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
      />
    </div>
  );
}
