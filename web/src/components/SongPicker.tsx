import { useState, useRef, useCallback } from "react";
import { useRecordingSearch } from "../hooks";
import type { Recording } from "../types";
import { formatDuration, artistName } from "../utils";

interface SongPickerProps {
  label: string;
  selected: Recording | null;
  onSelect: (r: Recording | null) => void;
}

export function SongPicker({ label, selected, onSelect }: SongPickerProps) {
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
