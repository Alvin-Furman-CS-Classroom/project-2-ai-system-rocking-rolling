import { Suspense } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { energyArcSketch } from '../sketches/energyArc';

const TRACKS = [
  { num: 1, name: 'Track 1', artist: 'Artist A', violation: false },
  { num: 2, name: 'Track 2', artist: 'Artist B', violation: false },
  { num: 3, name: 'Track 3', artist: 'Artist A', violation: true },
  { num: 4, name: 'Track 4', artist: 'Artist C', violation: false },
  { num: 5, name: 'Track 5', artist: 'Artist D', violation: false },
] as const;

export function Constraints({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Shaping the Playlist</h2>
      <p className="slide-subtitle">Constraint Satisfaction & Assembly</p>

      {/* Track list */}
      <div className="card" style={{ position: 'absolute', top: 152, left: 60, right: 60, padding: '4px 0' }}>
        {TRACKS.map(t => (
          <div
            key={t.num}
            style={{
              display: 'flex', alignItems: 'center',
              padding: '6px 16px',
              background: t.violation ? '#fff4ee' : 'transparent',
              borderRadius: t.violation ? 4 : 0,
              margin: t.violation ? '2px 4px' : '2px 0',

            }}
          >
            <span style={{ width: 32, fontWeight: 'bold', color: '#e8590c', textAlign: 'center', flexShrink: 0 }}>
              {t.num}
            </span>
            <span style={{ width: 200, fontWeight: 'bold', fontSize: 15 }}>{t.name}</span>
            <span style={{
              width: 220, fontSize: 15,
              color: t.violation ? '#e8590c' : '#9ca3af',
              fontWeight: t.violation ? 'bold' : 'normal',
            }}>
              {t.artist}
            </span>
            {t.violation && (
              <span style={{ marginLeft: 'auto', fontSize: 14, fontWeight: 'bold', color: '#e8590c' }}>
                ✗ repeat artist
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Two constraint cards */}
      <div style={{ position: 'absolute', top: 368, left: 60, right: 60, display: 'flex', gap: 60, bottom: 30 }}>
        {/* Hard constraint */}
        <div className="card card--orange" style={{ flex: 1, padding: '20px 24px' }}>
          <h3 style={{ color: '#e8590c', fontSize: 20, marginBottom: 10 }}>Hard: No Repeat Artists</h3>
          <p style={{ marginBottom: 12 }}>
            Track 3 violates → min-conflicts resolver swaps in a new track from the search space.
          </p>
          <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic' }}>
            Other hard constraints:
            <br />• No repeated tracks (MBID dedup)
          </p>
        </div>

        {/* Soft constraint with energy arc */}
        <div className="card" style={{ flex: 1, padding: '20px 24px' }}>
          <h3 style={{ fontSize: 20, marginBottom: 10, color: '#e8590c' }}>Soft: Energy Arc</h3>
          <Suspense fallback={null}>
            <P5Canvas sketch={energyArcSketch} isActive={isActive} replayKey={replayKey} />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
