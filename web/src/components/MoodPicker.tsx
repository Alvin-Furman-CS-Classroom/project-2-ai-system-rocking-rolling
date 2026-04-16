import type { MoodLabel } from "../types";

interface MoodPickerProps {
  value: MoodLabel | null;
  onChange: (mood: MoodLabel) => void;
}

const MOODS: { label: MoodLabel; display: string; colors: string }[] = [
  {
    label: "calm",
    display: "Calm",
    colors:
      "border-blue-600 bg-blue-600/20 text-blue-300 hover:bg-blue-600/40 data-[selected=true]:bg-blue-600 data-[selected=true]:text-white",
  },
  {
    label: "energized",
    display: "Energized",
    colors:
      "border-orange-500 bg-orange-500/20 text-orange-300 hover:bg-orange-500/40 data-[selected=true]:bg-orange-500 data-[selected=true]:text-white",
  },
  {
    label: "happy",
    display: "Happy",
    colors:
      "border-yellow-400 bg-yellow-400/20 text-yellow-300 hover:bg-yellow-400/40 data-[selected=true]:bg-yellow-400 data-[selected=true]:text-gray-900",
  },
  {
    label: "sad",
    display: "Sad",
    colors:
      "border-purple-500 bg-purple-500/20 text-purple-300 hover:bg-purple-500/40 data-[selected=true]:bg-purple-500 data-[selected=true]:text-white",
  },
  {
    label: "intense",
    display: "Intense",
    colors:
      "border-red-500 bg-red-500/20 text-red-300 hover:bg-red-500/40 data-[selected=true]:bg-red-500 data-[selected=true]:text-white",
  },
  {
    label: "chill",
    display: "Chill",
    colors:
      "border-teal-500 bg-teal-500/20 text-teal-300 hover:bg-teal-500/40 data-[selected=true]:bg-teal-500 data-[selected=true]:text-white",
  },
];

export function MoodPicker({ value, onChange }: MoodPickerProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {MOODS.map(({ label, display, colors }) => (
        <button
          key={label}
          type="button"
          data-selected={value === label}
          onClick={() => onChange(label)}
          className={`rounded-full border px-3 py-1 text-sm font-medium transition cursor-pointer ${colors}`}
        >
          {display}
        </button>
      ))}
    </div>
  );
}
