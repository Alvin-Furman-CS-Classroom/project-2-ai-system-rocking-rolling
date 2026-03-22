import { useState, useRef, useCallback } from "react";
import { $api, type SongSearchResult } from "../api/search/client";

interface SongPickerProps {
	label: string;
	selected: SongSearchResult | null;
	onSelect: (r: SongSearchResult | null) => void;
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

	const { data, isLoading } = $api.useQuery(
		"get",
		"/search/songs",
		{
			params: { query: { q: debouncedQuery } },
		},
		{ enabled: !!debouncedQuery },
	);

	return (
		<div className="flex-1 min-w-0">
			<label className="block text-sm font-medium text-gray-400 mb-2">
				{label}
			</label>
			{selected ? (
				<div className="rounded-lg border border-gray-700 bg-gray-800 p-4 flex items-center gap-3">
					<div className="min-w-0 flex-1">
						<p className="font-semibold text-white truncate">
							{selected.recording_name}
						</p>
						<p className="text-sm text-gray-400 truncate">
							{selected.artist_credit_name}
						</p>
					</div>
					{/*<span className="text-xs text-gray-500 shrink-0">
						{formatDuration(selected.duration)}
					</span>*/}
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
							{data?.length === 0 && !isLoading && (
								<li className="px-4 py-3 text-sm text-gray-500">
									No results found.
								</li>
							)}
							{data?.map((r) => (
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
											{r.recording_name}
										</p>
										<p className="text-xs text-gray-400 truncate">
											{r.artist_credit_name}
										</p>
										<p className="text-xs text-gray-400 truncate">
											{r.release_name}
										</p>
									</div>
									{/*<span className="text-xs text-gray-500 shrink-0">
										{r.artist_credit_name}
									</span>*/}
								</li>
							))}
						</ul>
					)}
				</div>
			)}
		</div>
	);
}
