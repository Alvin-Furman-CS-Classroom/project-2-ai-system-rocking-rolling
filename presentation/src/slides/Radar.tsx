import { Suspense, useState } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { radarSketch, SONGS, DIMS } from '../sketches/radar';

export function Radar({ isActive, replayKey }: SlideProps) {
  const [selectedSong, setSelectedSong] = useState(0);
  const song = SONGS[selectedSong];

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Hearing Music as Numbers</h2>
      <p className="slide-subtitle">12-dimensional feature vector per track</p>

      {/* Left panel: radar chart */}
      <div style={{ position: 'absolute', top: 150, left: 60 }}>
        <Suspense fallback={null}>
          <P5Canvas
            sketch={radarSketch}
            isActive={isActive}
            replayKey={replayKey}
            selectedSong={selectedSong}
          />
        </Suspense>
      </div>

      {/* Right panel: song selector + info */}
      <div style={{ position: 'absolute', top: 150, left: 640, right: 60, bottom: 60 }}>
        {/* Song buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {SONGS.map((s, i) => (
            <button
              key={i}
              className={`btn ${selectedSong === i ? 'active' : ''}`}
              onClick={() => setSelectedSong(i)}
              style={{ textAlign: 'left', padding: '10px 16px' }}
            >
              <span style={{ fontWeight: 'bold', display: 'block' }}>{s.name}</span>
              <span style={{ color: '#9ca3af', fontSize: 13 }}>{s.artist}</span>
            </button>
          ))}
        </div>

        {/* Song info card */}
        <div className="card card--orange" style={{ marginTop: 24 }}>
          <h3 style={{ color: '#e8590c', marginBottom: 12 }}>{song.name}</h3>
          <p style={{ color: '#9ca3af', marginBottom: 16, fontSize: 14, fontStyle: 'italic' }}>
            {song.artist}
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 12px' }}>
            {DIMS.map((dim, i) => (
              <span
                key={dim}
                style={{
                  fontSize: 12,
                  color: i % 2 === 0 ? '#e8590c' : '#1a1a1a',

                }}
              >
                {dim}: <strong>{Math.round(song.vals[i] * 100)}%</strong>
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
