import type { SongSearchResult } from "../api/search/client";
import type { InputMode, MoodLabel } from "../types";
import { MoodPicker } from "./MoodPicker";
import { SongPicker } from "./SongPicker";

interface EndpointInputProps {
  label: string;
  mode: InputMode;
  song: SongSearchResult | null;
  mood: MoodLabel | null;
  onModeChange: (m: InputMode) => void;
  onSongChange: (r: SongSearchResult | null) => void;
  onMoodChange: (m: MoodLabel) => void;
  onReset: () => void;
}

function EndpointInput({
  label,
  mode,
  song,
  mood,
  onModeChange,
  onSongChange,
  onMoodChange,
  onReset,
}: EndpointInputProps) {
  return (
    <div className="flex-1 flex flex-col gap-2">
      {/* Mode toggle */}
      <div className="flex items-center gap-1">
        <span className="text-sm font-medium text-gray-400 mr-2">{label}</span>
        <div className="flex rounded-lg overflow-hidden border border-gray-700">
          <button
            type="button"
            onClick={() => {
              onModeChange("track");
              onReset();
            }}
            className={`px-3 py-1 text-xs font-medium transition cursor-pointer ${
              mode === "track"
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            Song
          </button>
          <button
            type="button"
            onClick={() => {
              onModeChange("mood");
              onReset();
            }}
            className={`px-3 py-1 text-xs font-medium transition cursor-pointer ${
              mode === "mood"
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-400 hover:bg-gray-700"
            }`}
          >
            Mood
          </button>
        </div>
      </div>

      {mode === "track" ? (
        <SongPicker
          label=""
          selected={song}
          onSelect={(r) => {
            onSongChange(r);
            onReset();
          }}
        />
      ) : (
        <div className="rounded-lg border border-gray-700 bg-gray-800/50 p-3">
          <MoodPicker
            value={mood}
            onChange={(m) => {
              onMoodChange(m);
              onReset();
            }}
          />
        </div>
      )}
    </div>
  );
}

interface PlaylistFormProps {
  sourceMode: InputMode;
  destMode: InputMode;
  playlistSource: SongSearchResult | null;
  playlistDest: SongSearchResult | null;
  sourceMood: MoodLabel | null;
  destMood: MoodLabel | null;
  playlistLength: number;
  beamWidth: number;
  isPending: boolean;
  onSourceModeChange: (m: InputMode) => void;
  onDestModeChange: (m: InputMode) => void;
  onSourceChange: (r: SongSearchResult | null) => void;
  onDestChange: (r: SongSearchResult | null) => void;
  onSourceMoodChange: (m: MoodLabel) => void;
  onDestMoodChange: (m: MoodLabel) => void;
  onLengthChange: (length: number) => void;
  onBeamWidthChange: (width: number) => void;
  onSubmit: () => void;
  onReset: () => void;
}

export function PlaylistForm({
  sourceMode,
  destMode,
  playlistSource,
  playlistDest,
  sourceMood,
  destMood,
  playlistLength,
  beamWidth,
  isPending,
  onSourceModeChange,
  onDestModeChange,
  onSourceChange,
  onDestChange,
  onSourceMoodChange,
  onDestMoodChange,
  onLengthChange,
  onBeamWidthChange,
  onSubmit,
  onReset,
}: PlaylistFormProps) {
  const sourceReady =
    sourceMode === "track" ? !!playlistSource : !!sourceMood;
  const destReady = destMode === "track" ? !!playlistDest : !!destMood;
  const canSubmit = sourceReady && destReady && !isPending;

  return (
    <>
      <div className="flex flex-col sm:flex-row gap-4 mb-8">
        <EndpointInput
          label="Start"
          mode={sourceMode}
          song={playlistSource}
          mood={sourceMood}
          onModeChange={onSourceModeChange}
          onSongChange={onSourceChange}
          onMoodChange={onSourceMoodChange}
          onReset={onReset}
        />
        <EndpointInput
          label="End"
          mode={destMode}
          song={playlistDest}
          mood={destMood}
          onModeChange={onDestModeChange}
          onSongChange={onDestChange}
          onMoodChange={onDestMoodChange}
          onReset={onReset}
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
          disabled={!canSubmit}
          className="rounded-lg bg-indigo-600 px-8 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
        >
          {isPending ? "Generating…" : "Generate Playlist"}
        </button>
      </div>
    </>
  );
}
