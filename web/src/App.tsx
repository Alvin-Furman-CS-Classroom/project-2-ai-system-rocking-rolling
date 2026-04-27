import { useState } from "react";
import {
	TabNavigation,
	SongPicker,
	ResultsPanel,
	PlaylistResults,
	PlaylistForm,
} from "./components";
import { useCompare, usePlaylistGenerator } from "./hooks";
import type { SongSearchResult } from "./api/search/client";

function App() {
	const [activeTab, setActiveTab] = useState<"compare" | "playlist">("compare");
	const [songA, setSongA] = useState<SongSearchResult | null>(null);
	const [songB, setSongB] = useState<SongSearchResult | null>(null);
	const compare = useCompare();

	const [playlistSource, setPlaylistSource] = useState<SongSearchResult | null>(
		null,
	);
	const [playlistDest, setPlaylistDest] = useState<SongSearchResult | null>(
		null,
	);
	const [playlistLength, setPlaylistLength] = useState(7);
	const [beamWidth, setBeamWidth] = useState(10);
	const generatePlaylist = usePlaylistGenerator();

	const handleCompare = () => {
		if (songA && songB) {
			compare.mutate({ id1: songA.recording_mbid, id2: songB.recording_mbid });
		}
	};

	const handleGeneratePlaylist = () => {
		if (playlistSource && playlistDest) {
			generatePlaylist.mutate({
				sourceId: playlistSource.recording_mbid,
				destId: playlistDest.recording_mbid,
				length: playlistLength,
				beamWidth,
			});
		}
	};

	return (
		<div className="min-h-screen bg-gray-950 text-white">
			<div className="mx-auto max-w-3xl px-4 py-16">
				<h1 className="text-3xl font-bold text-center mb-2">
					{activeTab === "compare" ? "Song Similarity" : "Playlist Generator"}
				</h1>
				<p className="text-center text-gray-400 mb-10">
					{activeTab === "compare"
						? "Pick two songs and compare how similar they are."
						: "Generate a playlist path between two songs using beam search."}
				</p>

				<TabNavigation activeTab={activeTab} onTabChange={setActiveTab} />

				{activeTab === "compare" ? (
					<>
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
					</>
				) : (
					<>
						<PlaylistForm
							playlistSource={playlistSource}
							playlistDest={playlistDest}
							playlistLength={playlistLength}
							beamWidth={beamWidth}
							isPending={generatePlaylist.isPending}
							onSourceChange={setPlaylistSource}
							onDestChange={setPlaylistDest}
							onLengthChange={setPlaylistLength}
							onBeamWidthChange={setBeamWidth}
							onSubmit={handleGeneratePlaylist}
							onReset={generatePlaylist.reset}
						/>

						{generatePlaylist.isError && (
							<div className="mt-6 rounded-lg border border-red-800 bg-red-950 p-4 text-center text-sm text-red-400">
								{generatePlaylist.error.message}
							</div>
						)}

						{generatePlaylist.data && (
							<PlaylistResults result={generatePlaylist.data} />
						)}
					</>
				)}
			</div>
		</div>
	);
}

export default App;
