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

export function DemoPreferences({ isActive, demoState, onNext }: DemoSlideProps) {
  const { selectedGenres, selectedArtists } = demoState;

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Your Taste Profile</h2>
      <p className="slide-subtitle">Here's what we know about you</p>

      <div style={{
        position: 'absolute',
        top: 155,
        left: T.MARGIN,
        right: T.MARGIN,
        bottom: 80,
        display: 'flex',
        gap: 32,
      }}>
        {/* Genres column */}
        <div
          className="card animate-item"
          style={{ flex: 1, padding: '24px 28px', animationDelay: '0.1s' }}
        >
          <p style={{ fontSize: 13, color: T.MUTED, fontStyle: 'italic', marginBottom: 14 }}>
            Genres
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {selectedGenres.map(g => (
              <span
                key={g}
                className="card card--orange"
                style={{
                  padding: '6px 16px',
                  fontSize: 15,
                  fontWeight: 'bold',
                  color: T.ORANGE,
                  borderRadius: 20,
                  display: 'inline-block',
                }}
              >
                {GENRE_DISPLAY[g] ?? g}
              </span>
            ))}
          </div>
        </div>

        {/* Artists column */}
        <div
          className="card animate-item"
          style={{ flex: 2, padding: '24px 28px', animationDelay: '0.2s', overflowY: 'auto' }}
        >
          <p style={{ fontSize: 13, color: T.MUTED, fontStyle: 'italic', marginBottom: 14 }}>
            Favorite Artists
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {selectedArtists.map((artist, i) => (
              <div
                key={artist}
                className="animate-item"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  animationDelay: `${0.25 + i * 0.06}s`,
                }}
              >
                <span style={{
                  width: 8, height: 8, borderRadius: '50%',
                  background: T.ORANGE, flexShrink: 0,
                }} />
                <span style={{ fontSize: 16, fontWeight: 'bold' }}>{artist}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <button
        className="btn"
        onClick={() => onNext?.()}
        style={{
          position: 'absolute',
          bottom: 28,
          right: T.MARGIN,
          padding: '10px 28px',
          fontSize: 15,
          fontWeight: 'bold',
          background: T.ORANGE,
          color: '#fff',
          borderColor: T.ORANGE,
        }}
      >
        Set Your Mood Journey →
      </button>
    </div>
  );
}
