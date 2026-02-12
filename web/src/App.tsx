import { useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { MusicBrainzClient } from "@kellnerd/musicbrainz";

const client = new MusicBrainzClient({
  app: { name: "SongSimilarity", version: "0.1.0" },
});

interface ArtistCredit {
  name: string;
  joinphrase: string;
}

interface Recording {
  id: string;
  title: string;
  length: number | null;
  "artist-credit"?: ArtistCredit[];
  "first-release-date"?: string;
}

interface SearchResponse {
  recordings: Recording[];
  count: number;
}

function formatDuration(ms: number | null): string {
  if (ms === null) return "?:??";
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

function artistName(recording: Recording): string {
  return (
    recording["artist-credit"]
      ?.map((c) => c.name + (c.joinphrase ?? ""))
      .join("") ?? "Unknown Artist"
  );
}

function stubSimilarityScore(_a: Recording, _b: Recording): number {
  return Math.round(Math.random() * 100);
}

function useRecordingSearch(query: string) {
  return useQuery<SearchResponse>({
    queryKey: ["recording-search", query],
    queryFn: async () => {
      const res = await client.get("recording", {
        query,
        limit: 10,
      });
      return res as SearchResponse;
    },
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000,
  });
}

function SongPicker({
  label,
  selected,
  onSelect,
}: {
  label: string;
  selected: Recording | null;
  onSelect: (r: Recording | null) => void;
}) {
  const [query, setQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [open, setOpen] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>>(null);

  const debounce = useCallback((value: string) => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setDebouncedQuery(value), 400);
  }, []);

  const { data, isLoading } = useRecordingSearch(debouncedQuery);

  return (
    <div className="flex-1 min-w-0">
      <label className="block text-sm font-medium text-gray-400 mb-2">
        {label}
      </label>
      {selected ? (
        <div className="rounded-lg border border-gray-700 bg-gray-800 p-4 flex items-center gap-3">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-white truncate">
              {selected.title}
            </p>
            <p className="text-sm text-gray-400 truncate">
              {artistName(selected)}
            </p>
            {selected["first-release-date"] && (
              <p className="text-xs text-gray-500">
                {selected["first-release-date"]}
              </p>
            )}
          </div>
          <span className="text-xs text-gray-500 shrink-0">
            {formatDuration(selected.length)}
          </span>
          <button
            onClick={() => onSelect(null)}
            className="text-gray-500 hover:text-white ml-2 cursor-pointer"
            aria-label="Clear selection"
          >
            &times;
          </button>
        </div>
      ) : (
        <div className="relative">
          <input
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              debounce(e.target.value);
              setOpen(true);
            }}
            onFocus={() => setOpen(true)}
            placeholder="Search for a song…"
            className="w-full rounded-lg border border-gray-700 bg-gray-800 px-4 py-3 text-white placeholder-gray-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none"
          />
          {open && debouncedQuery.length >= 2 && (
            <ul className="absolute z-10 mt-1 max-h-64 w-full overflow-y-auto rounded-lg border border-gray-700 bg-gray-800 shadow-lg">
              {isLoading && (
                <li className="px-4 py-3 text-sm text-gray-500">Searching…</li>
              )}
              {data?.recordings.length === 0 && !isLoading && (
                <li className="px-4 py-3 text-sm text-gray-500">
                  No results found.
                </li>
              )}
              {data?.recordings.map((r) => (
                <li
                  key={r.id}
                  onClick={() => {
                    onSelect(r);
                    setQuery("");
                    setDebouncedQuery("");
                    setOpen(false);
                  }}
                  className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-gray-700"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-white truncate">
                      {r.title}
                    </p>
                    <p className="text-xs text-gray-400 truncate">
                      {artistName(r)}
                    </p>
                  </div>
                  <span className="text-xs text-gray-500 shrink-0">
                    {formatDuration(r.length)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function App() {
  const [songA, setSongA] = useState<Recording | null>(null);
  const [songB, setSongB] = useState<Recording | null>(null);
  const [score, setScore] = useState<number | null>(null);

  const handleCompare = () => {
    if (songA && songB) {
      setScore(stubSimilarityScore(songA, songB));
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <div className="mx-auto max-w-3xl px-4 py-16">
        <h1 className="text-3xl font-bold text-center mb-2">Song Similarity</h1>
        <p className="text-center text-gray-400 mb-10">
          Pick two songs and compare how similar they are.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <SongPicker
            label="Song A"
            selected={songA}
            onSelect={(r) => {
              setSongA(r);
              setScore(null);
            }}
          />
          <SongPicker
            label="Song B"
            selected={songB}
            onSelect={(r) => {
              setSongB(r);
              setScore(null);
            }}
          />
        </div>

        <div className="text-center">
          <button
            onClick={handleCompare}
            disabled={!songA || !songB}
            className="rounded-lg bg-indigo-600 px-8 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            Compare
          </button>
        </div>

        {score !== null && songA && songB && (
          <div className="mt-10 rounded-xl border border-gray-800 bg-gray-900 p-8 text-center">
            <p className="text-sm text-gray-400 mb-1">Similarity Score</p>
            <p className="text-6xl font-bold tabular-nums">
              {score}
              <span className="text-2xl text-gray-500">%</span>
            </p>
            <p className="mt-4 text-sm text-gray-500">
              {songA.title} vs {songB.title}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
