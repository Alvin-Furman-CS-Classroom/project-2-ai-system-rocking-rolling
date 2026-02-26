import type { TabType } from "../types";

interface TabNavigationProps {
  activeTab: TabType;
  onTabChange: (tab: TabType) => void;
}

export function TabNavigation({ activeTab, onTabChange }: TabNavigationProps) {
  return (
    <div className="flex justify-center mb-8">
      <div className="inline-flex rounded-lg border border-gray-800 bg-gray-900 p-1">
        <button
          onClick={() => onTabChange("compare")}
          className={`px-6 py-2 rounded-md text-sm font-medium transition ${
            activeTab === "compare"
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Compare
        </button>
        <button
          onClick={() => onTabChange("playlist")}
          className={`px-6 py-2 rounded-md text-sm font-medium transition ${
            activeTab === "playlist"
              ? "bg-indigo-600 text-white"
              : "text-gray-400 hover:text-white"
          }`}
        >
          Playlist
        </button>
      </div>
    </div>
  );
}
