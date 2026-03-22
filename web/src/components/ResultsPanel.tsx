import type { SongSearchResult } from "../api/search/client";
import type { CompareResponse, CompareComponents } from "../types";
import { ComponentBar, COMPONENT_LABELS } from "./ComponentBar";

interface ResultsPanelProps {
	result: CompareResponse;
	songA: SongSearchResult;
	songB: SongSearchResult;
}

export function ResultsPanel({ result, songA, songB }: ResultsPanelProps) {
	return (
		<div className="mt-10 rounded-xl border border-gray-800 bg-gray-900 p-8">
			<div className="text-center mb-8">
				<p className="text-sm text-gray-400 mb-1">Similarity Score</p>
				<p className="text-6xl font-bold tabular-nums">
					{Math.round(result.score * 100)}
					<span className="text-2xl text-gray-500">%</span>
				</p>
				<p className="mt-2 text-sm text-gray-500">
					{songA.recording_name} vs {songB.recording_name}
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
