import type { DemoSlideProps } from './demo-types';
import { T } from '../theme';

const GENRE_DISPLAY: Record<string, string> = {
  rock: 'Rock',
  pop: 'Pop',
  electronic: 'Electronic',
  'hip-hop': 'Hip-Hop',
  jazz: 'Jazz',
  classical: 'Classical',
  folk: 'Folk / Country',
};

const GENRE_KEYS = Object.keys(GENRE_DISPLAY);

export function DemoGenres({ isActive, demoState, setDemoState, onNext }: DemoSlideProps) {
  const { selectedGenres } = demoState;

  function toggle(genre: string) {
    const isSelected = selectedGenres.includes(genre);
    setDemoState(s => ({
      ...s,
      selectedGenres: isSelected
        ? s.selectedGenres.filter(g => g !== genre)
        : [...s.selectedGenres, genre],
      // Reset downstream state when genre selection changes
      selectedArtists: [],
      startTrack: null,
      endTrack: null,
      playlist: null,
    }));
  }

  const canAdvance = selectedGenres.length > 0;

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Pick Your Genres</h2>
      <p className="slide-subtitle">What kind of music are you into?</p>

      {/* Genre grid — 4 across top row, 3 centered below */}
      <div style={{
        position: 'absolute',
        top: 155,
        left: T.MARGIN,
        right: T.MARGIN,
        bottom: 80,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        gap: 16,
      }}>
        {/* Row 1: 4 cards */}
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
          {GENRE_KEYS.slice(0, 4).map(genre => (
            <GenreCard
              key={genre}
              genre={genre}
              display={GENRE_DISPLAY[genre]}
              selected={selectedGenres.includes(genre)}
              onToggle={() => toggle(genre)}
            />
          ))}
        </div>
        {/* Row 2: 3 cards */}
        <div style={{ display: 'flex', gap: 16, justifyContent: 'center' }}>
          {GENRE_KEYS.slice(4).map(genre => (
            <GenreCard
              key={genre}
              genre={genre}
              display={GENRE_DISPLAY[genre]}
              selected={selectedGenres.includes(genre)}
              onToggle={() => toggle(genre)}
            />
          ))}
        </div>
      </div>

      {/* Continue button */}
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
        Continue →
      </button>
    </div>
  );
}

function GenreCard({
  genre,
  display,
  selected,
  onToggle,
}: {
  genre: string;
  display: string;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <div
      onClick={onToggle}
      style={{
        width: 260,
        height: 110,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        cursor: 'pointer',
        borderRadius: 6,
        border: `2px solid ${selected ? T.ORANGE : T.BORDER}`,
        background: selected ? T.ORANGE_L : T.SURFACE,
        transition: 'border-color 0.15s, background 0.15s',
        userSelect: 'none',
      }}
    >
      <span style={{ fontSize: 28 }}>{GENRE_EMOJI[genre]}</span>
      <span style={{
        fontSize: 18,
        fontWeight: 'bold',
        color: selected ? T.ORANGE : T.TEXT,
        fontFamily: 'var(--font-heading)',
      }}>
        {display}
      </span>
    </div>
  );
}

const GENRE_EMOJI: Record<string, string> = {
  rock: '🎸',
  pop: '🎤',
  electronic: '🎛️',
  'hip-hop': '🎧',
  jazz: '🎷',
  classical: '🎻',
  folk: '🪕',
};
