import type { DemoSlideProps, MoodLabel } from './demo-types';
import { T } from '../theme';

const MOODS: { label: string; value: MoodLabel; color: string }[] = [
  { label: 'Calm',      value: 'calm',      color: '#60a5fa' },
  { label: 'Chill',     value: 'chill',     color: '#2dd4bf' },
  { label: 'Happy',     value: 'happy',     color: '#facc15' },
  { label: 'Sad',       value: 'sad',       color: '#a78bfa' },
  { label: 'Energized', value: 'energized', color: '#fb923c' },
  { label: 'Intense',   value: 'intense',   color: '#f87171' },
];

export function DemoMoodJourney({ isActive, demoState, setDemoState, onNext }: DemoSlideProps) {
  const { startMood, endMood } = demoState;

  const canAdvance = startMood !== null && endMood !== null;

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Your Mood Journey</h2>
      <p className="slide-subtitle">Where are you starting, and where do you want to end up?</p>

      <div style={{
        position: 'absolute',
        top: 155,
        left: T.MARGIN,
        right: T.MARGIN,
        bottom: 80,
        display: 'flex',
        gap: 0,
      }}>
        {/* Start mood */}
        <MoodPicker
          label="Where are you now?"
          selected={startMood}
          onSelect={mood => setDemoState(s => ({ ...s, startMood: mood, startTrack: null, playlist: null }))}
        />

        {/* Divider with arrow */}
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          width: 60,
          gap: 8,
          flexShrink: 0,
        }}>
          <div style={{ width: 1, flex: 1, background: T.BORDER }} />
          <span style={{ fontSize: 22, color: T.MUTED }}>→</span>
          <div style={{ width: 1, flex: 1, background: T.BORDER }} />
        </div>

        {/* End mood */}
        <MoodPicker
          label="Where do you want to end up?"
          selected={endMood}
          onSelect={mood => setDemoState(s => ({ ...s, endMood: mood, endTrack: null, playlist: null }))}
        />
      </div>

      {/* Continue */}
      <button
        className="btn"
        onClick={() => canAdvance && onNext?.()}
        style={{
          position: 'absolute',
          bottom: 28,
          right: T.MARGIN,
          padding: '10px 28px',
          fontSize: 15,
          fontWeight: 'bold',
          background: canAdvance ? T.ORANGE : undefined,
          color: canAdvance ? '#fff' : undefined,
          borderColor: canAdvance ? T.ORANGE : undefined,
          opacity: canAdvance ? 1 : 0.35,
          cursor: canAdvance ? 'pointer' : 'not-allowed',
        }}
      >
        Find My Tracks →
      </button>
    </div>
  );
}

function MoodPicker({
  label,
  selected,
  onSelect,
}: {
  label: string;
  selected: MoodLabel | null;
  onSelect: (m: MoodLabel) => void;
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 16, padding: '0 20px' }}>
      <p style={{
        fontSize: 15,
        color: T.MUTED,
        fontStyle: 'italic',
        fontFamily: 'var(--font-heading)',
        textAlign: 'center',
      }}>
        {label}
      </p>
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1fr',
        gap: 12,
      }}>
        {MOODS.map(m => {
          const isSelected = selected === m.value;
          return (
            <button
              key={m.value}
              onClick={() => onSelect(m.value)}
              style={{
                padding: '16px 12px',
                borderRadius: 6,
                border: `2px solid ${isSelected ? m.color : T.BORDER}`,
                background: isSelected ? `${m.color}18` : T.SURFACE,
                cursor: 'pointer',
                fontSize: 15,
                fontWeight: isSelected ? 'bold' : 'normal',
                color: isSelected ? m.color : T.TEXT,
                transition: 'border-color 0.15s, background 0.15s',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
              }}
            >
              {isSelected && (
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: m.color, flexShrink: 0,
                }} />
              )}
              {m.label}
            </button>
          );
        })}
      </div>

      {/* Selected mood display */}
      {selected && (
        <div style={{
          marginTop: 8,
          padding: '10px 16px',
          borderRadius: 6,
          background: `${MOODS.find(m => m.value === selected)?.color ?? T.ORANGE}18`,
          border: `1.5px solid ${MOODS.find(m => m.value === selected)?.color ?? T.ORANGE}`,
          textAlign: 'center',
        }}>
          <span style={{
            fontSize: 14,
            fontWeight: 'bold',
            color: MOODS.find(m => m.value === selected)?.color ?? T.ORANGE,
          }}>
            ✓ {MOODS.find(m => m.value === selected)?.label}
          </span>
        </div>
      )}
    </div>
  );
}
