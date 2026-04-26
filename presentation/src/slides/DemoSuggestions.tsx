import type { DemoSlideProps, CuratedTrack, MoodLabel } from './demo-types';
import { T } from '../theme';
import curatedTracksData from '../data/curated_tracks.json';

const curatedTracks = curatedTracksData as CuratedTrack[];

const MOOD_COLORS: Record<MoodLabel, string> = {
  calm:      '#60a5fa',
  chill:     '#2dd4bf',
  happy:     '#facc15',
  sad:       '#a78bfa',
  energized: '#fb923c',
  intense:   '#f87171',
};

function getSuggestions(mood: MoodLabel, genres: string[], count = 4): CuratedTrack[] {
  const byMoodAndGenre = curatedTracks.filter(t => t.mood === mood && genres.includes(t.genre));
  const pool = byMoodAndGenre.length >= count
    ? byMoodAndGenre
    : curatedTracks.filter(t => t.mood === mood);
  // Stable ordering by mbid so suggestions don't jump around on re-render
  return [...pool].sort((a, b) => a.mbid.localeCompare(b.mbid)).slice(0, count);
}

export function DemoSuggestions({ isActive, demoState, setDemoState, onNext }: DemoSlideProps) {
  const { startMood, endMood, selectedGenres, startTrack, endTrack } = demoState;

  const startSuggestions = startMood ? getSuggestions(startMood, selectedGenres) : [];
  const endSuggestions   = endMood   ? getSuggestions(endMood,   selectedGenres) : [];

  const canAdvance = startTrack !== null && endTrack !== null;

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Pick Your Anchor Tracks</h2>
      <p className="slide-subtitle">Choose one track to start with and one to end on</p>

      <div style={{
        position: 'absolute',
        top: 155,
        left: T.MARGIN,
        right: T.MARGIN,
        bottom: 80,
        display: 'flex',
        gap: 24,
      }}>
        {/* Start column */}
        <TrackColumn
          label={`Start  —  ${startMood ?? ''}`}
          moodColor={startMood ? MOOD_COLORS[startMood] : T.ORANGE}
          tracks={startSuggestions}
          selected={startTrack}
          onSelect={t => setDemoState(s => ({ ...s, startTrack: t, playlist: null }))}
        />

        {/* Divider */}
        <div style={{ width: 1, background: T.BORDER, flexShrink: 0, margin: '0 4px' }} />

        {/* End column */}
        <TrackColumn
          label={`End  —  ${endMood ?? ''}`}
          moodColor={endMood ? MOOD_COLORS[endMood] : T.ORANGE}
          tracks={endSuggestions}
          selected={endTrack}
          onSelect={t => setDemoState(s => ({ ...s, endTrack: t, playlist: null }))}
        />
      </div>

      {/* Generate button */}
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
        Generate Playlist →
      </button>
    </div>
  );
}

function TrackColumn({
  label,
  moodColor,
  tracks,
  selected,
  onSelect,
}: {
  label: string;
  moodColor: string;
  tracks: CuratedTrack[];
  selected: CuratedTrack | null;
  onSelect: (t: CuratedTrack) => void;
}) {
  return (
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <p style={{
        fontSize: 13,
        color: moodColor,
        fontStyle: 'italic',
        fontWeight: 'bold',
        textTransform: 'capitalize',
        marginBottom: 4,
      }}>
        {label}
      </p>

      {tracks.length === 0 ? (
        <p style={{ color: T.MUTED, fontStyle: 'italic', fontSize: 14 }}>
          No tracks available for this mood + genre combination.
        </p>
      ) : (
        tracks.map((track, i) => {
          const isSelected = selected?.mbid === track.mbid;
          return (
            <div
              key={track.mbid}
              onClick={() => onSelect(track)}
              className="animate-item"
              style={{
                padding: '12px 16px',
                borderRadius: 6,
                border: `2px solid ${isSelected ? moodColor : T.BORDER}`,
                background: isSelected ? `${moodColor}12` : T.BG,
                cursor: 'pointer',
                transition: 'border-color 0.15s, background 0.15s',
                animationDelay: `${i * 0.08}s`,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <p style={{
                  fontSize: 14,
                  fontWeight: 'bold',
                  color: isSelected ? moodColor : T.TEXT,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  maxWidth: '80%',
                }}>
                  {isSelected && '✓ '}{track.title ?? 'Unknown Title'}
                </p>
                {track.bpm && (
                  <span style={{ fontSize: 12, color: T.MUTED, flexShrink: 0 }}>
                    {track.bpm} BPM
                  </span>
                )}
              </div>
              <p style={{ fontSize: 13, color: T.MUTED, marginTop: 2 }}>
                {track.artist ?? 'Unknown Artist'}
              </p>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 6 }}>
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: moodColor, flexShrink: 0,
                }} />
                <span style={{ fontSize: 12, color: moodColor, textTransform: 'capitalize' }}>
                  {track.mood}
                </span>
                {track.key && (
                  <span style={{ fontSize: 12, color: T.MUTED, marginLeft: 6 }}>
                    {track.key} {track.scale}
                  </span>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
