import type { Recording } from "../types";
import { SongPicker } from "./SongPicker";

interface PlaylistFormProps {
  playlistSource: Recording | null;
  playlistDest: Recording | null;
  playlistLength: number;
  beamWidth: number;
  isPending: boolean;
  onSourceChange: (r: Recording | null) => void;
  onDestChange: (r: Recording | null) => void;
  onLengthChange: (length: number) => void;
  onBeamWidthChange: (width: number) => void;
  onSubmit: () => void;
  onReset: () => void;
}

export function PlaylistForm({
  playlistSource,
  playlistDest,
  playlistLength,
  beamWidth,
  isPending,
  onSourceChange,
  onDestChange,
  onLengthChange,
  onBeamWidthChange,
  onSubmit,
  onReset,
}: PlaylistFormProps) {
  return (
    <>
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <SongPicker
          label="Start Track"
          selected={playlistSource}
          onSelect={(r) => {
            onSourceChange(r);
            onReset();
          }}
        />
        <SongPicker
          label="End Track"
          selected={playlistDest}
          onSelect={(r) => {
            onDestChange(r);
            onReset();
          }}
        />
      </div>

      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Playlist Length
          </label>
          <input
            type="number"
            min="2"
            max="20"
            value={playlistLength}
            onChange={(e) => onLengthChange(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
        <div className="flex-1">
          <label className="block text-sm font-medium text-gray-400 mb-2">
            Beam Width
          </label>
          <input
            type="number"
            min="1"
            max="50"
            value={beamWidth}
            onChange={(e) => onBeamWidthChange(Number(e.target.value))}
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          />
        </div>
      </div>

      <div className="text-center">
        <button
          onClick={onSubmit}
          disabled={
            !playlistSource ||
            !playlistDest ||
            isPending
          }
          className="rounded-lg bg-indigo-600 px-8 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {isPending ? "Generating…" : "Generate Playlist"}
        </button>
      </div>
    </>
  );
}
