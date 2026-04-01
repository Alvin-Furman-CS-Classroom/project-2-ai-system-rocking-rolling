import { useEffect } from "react";
import type { TrackInfo } from "../types";
import { FeatureProgressionChart } from "./FeatureProgressionChart";

interface FeatureModalProps {
  tracks: TrackInfo[];
  isOpen: boolean;
  onClose: () => void;
}

export function FeatureModal({ tracks, isOpen, onClose }: FeatureModalProps) {
  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

      {/* Panel */}
      <div
        className="relative z-10 w-full max-w-2xl rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            Feature Progression
          </h3>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-800 hover:text-white transition cursor-pointer"
            aria-label="Close"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <FeatureProgressionChart tracks={tracks} compact={false} />

        {/* Per-track mood details */}
        <div className="mt-4 grid grid-cols-2 sm:grid-cols-3 gap-2">
          {tracks.map((track) => (
            <div
              key={track.position}
              className="rounded-lg bg-gray-800 px-3 py-2 text-xs"
            >
              <div className="font-medium text-white truncate">
                {track.position}. {track.title ?? `Track ${track.position}`}
              </div>
              <div className="text-gray-400 mt-0.5">
                {track.bpm ? `${Math.round(track.bpm)} BPM` : "—"}
                {track.energy != null
                  ? ` · ${(track.energy * 100).toFixed(0)}% energy`
                  : ""}
              </div>
              {track.mood_label && (
                <div className="text-gray-300 mt-0.5 capitalize">
                  {track.mood_label}
                  {track.mood_confidence != null
                    ? ` (${(track.mood_confidence * 100).toFixed(0)}%)`
                    : ""}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
