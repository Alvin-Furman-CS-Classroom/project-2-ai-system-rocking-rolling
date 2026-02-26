import { useState, useRef, useCallback } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
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

interface CompareComponents {
  key: number;
  tempo: number;
  energy: number;
  loudness: number;
  mood: number;
  timbre: number;
  genre: number;
}

interface CompareResponse {
  recording_id_1: string;
  recording_id_2: string;
  score: number;
  is_compatible: boolean;
  components: CompareComponents;
  violations: string[];
  explanation: string;
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

function useCompare() {
  return useMutation<CompareResponse, Error, { id1: string; id2: string }>({
    mutationFn: async ({ id1, id2 }) => {
      const res = await fetch(
        `/api/compare?recording_id_1=${encodeURIComponent(id1)}&recording_id_2=${encodeURIComponent(id2)}`,
      );
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        throw new Error(body?.error ?? `API error: ${res.status}`);
      }
      return res.json();
    },
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

const COMPONENT_LABELS: Record<keyof CompareComponents, string> = {
  key: "Key",
  tempo: "Tempo",
  energy: "Energy",
  loudness: "Loudness",
  mood: "Mood",
  timbre: "Timbre",
  genre: "Genre",
};

function scoreColor(score: number): string {
  if (score >= 0.7) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  return "bg-red-500";
}

function ComponentBar({ label, value }: { label: string; value: number }) {
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

function ResultsPanel({
  result,
  songA,
  songB,
}: {
  result: CompareResponse;
  songA: Recording;
  songB: Recording;
}) {
  return (
    <div className="mt-10 rounded-xl border border-gray-800 bg-gray-900 p-8">
      <div className="text-center mb-8">
        <p className="text-sm text-gray-400 mb-1">Similarity Score</p>
        <p className="text-6xl font-bold tabular-nums">
          {Math.round(result.score * 100)}
          <span className="text-2xl text-gray-500">%</span>
        </p>
        <p className="mt-2 text-sm text-gray-500">
          {songA.title} vs {songB.title}
        </p>
        <span
          className={`mt-2 inline-block rounded-full px-3 py-0.5 text-xs font-medium ${
            result.is_compatible
              ? "bg-emerald-500/20 text-emerald-400"
              : "bg-red-500/20 text-red-400"
          }`}
        >
          {result.is_compatible ? "Compatible" : "Incompatible"}
        </span>
      </div>

      <div className="space-y-3 mb-8">
        <h3 className="text-sm font-medium text-gray-300 mb-4">
          Component Breakdown
        </h3>
        {(
          Object.entries(COMPONENT_LABELS) as [
            keyof CompareComponents,
            string,
          ][]
        ).map(([key, label]) => (
          <ComponentBar
            key={key}
            label={label}
            value={result.components[key]}
          />
        ))}
      </div>

      {result.violations.length > 0 && (
        <div className="mb-6">
          <h3 className="text-sm font-medium text-gray-300 mb-2">Violations</h3>
          <ul className="space-y-1">
            {result.violations.map((v) => (
              <li
                key={v}
                className="text-sm text-red-400 flex items-start gap-2"
              >
                <span className="shrink-0 mt-0.5">!</span>
                {v}
              </li>
            ))}
          </ul>
        </div>
      )}

      {result.explanation && (
        <div>
          <h3 className="text-sm font-medium text-gray-300 mb-2">
            Explanation
          </h3>
          <pre className="text-xs text-gray-500 whitespace-pre-wrap font-mono bg-gray-800 rounded-lg p-4">
            {result.explanation}
          </pre>
        </div>
      )}
    </div>
  );
}

function App() {
  const [songA, setSongA] = useState<Recording | null>(null);
  const [songB, setSongB] = useState<Recording | null>(null);
  const compare = useCompare();

  const handleCompare = () => {
    if (songA && songB) {
      compare.mutate({ id1: songA.id, id2: songB.id });
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
              compare.reset();
            }}
          />
          <SongPicker
            label="Song B"
            selected={songB}
            onSelect={(r) => {
              setSongB(r);
              compare.reset();
            }}
          />
        </div>

        <div className="text-center">
          <button
            onClick={handleCompare}
            disabled={!songA || !songB || compare.isPending}
            className="rounded-lg bg-indigo-600 px-8 py-3 font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
          >
            {compare.isPending ? "Comparing…" : "Compare"}
          </button>
        </div>

        {compare.isError && (
          <div className="mt-6 rounded-lg border border-red-800 bg-red-950 p-4 text-center text-sm text-red-400">
            {compare.error.message}
          </div>
        )}

        {compare.data && songA && songB && (
          <ResultsPanel result={compare.data} songA={songA} songB={songB} />
        )}
      </div>
    </div>
  );
}

export default App;
