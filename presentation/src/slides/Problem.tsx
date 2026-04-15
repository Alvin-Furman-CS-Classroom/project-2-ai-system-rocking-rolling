import type { SlideProps } from './types';

const CARDS = [
  {
    heading: 'API Lockdown',
    body: 'Spotify restricted its recommendation API — proprietary systems are unsustainable.',
    orange: true,
  },
  {
    heading: 'Similarity ≠ Journey',
    body: 'Current playlists optimise for similarity alone, not musical journeys from A to B.',
    orange: false,
  },
  {
    heading: 'The Question',
    body: 'How do you get from Track A to Track B through a smooth sequence of waypoints?',
    orange: false,
  },
] as const;

export function Problem({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title animate-item" style={{ animationDelay: '0s' }}>
        The Problem with Modern Playlists
      </h2>

      <div style={{ position: 'absolute', top: 160, left: 60, right: 60 }}>
        {CARDS.map((card, i) => (
          <div
            key={i}
            className={`card animate-item ${card.orange ? 'card--orange' : ''}`}
            style={{
              marginBottom: 20,
              animationDelay: `${i * 0.25}s`,
            }}
          >
            <h3 style={{ color: card.orange ? '#e8590c' : '#1a1a1a' }}>{card.heading}</h3>
            <p>{card.body}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
