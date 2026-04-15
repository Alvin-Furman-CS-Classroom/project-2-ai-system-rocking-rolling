import { Suspense, useState } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { moodScatterSketch } from '../sketches/moodScatter';

const MOODS = ['Calm', 'Chill', 'Sad', 'Happy', 'Energized', 'Intense'] as const;

export function Mood({ isActive, replayKey }: SlideProps) {
  const [selectedMood, setSelectedMood] = useState(3); // default: Happy

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Mood to Music</h2>
      <p className="slide-subtitle">Supervised Classification — Logistic Regression / MLP / Ensemble</p>

      {/* Scatter plot */}
      <div style={{ position: 'absolute', top: 148, left: 90 }}>
        <Suspense fallback={null}>
          <P5Canvas
            sketch={moodScatterSketch}
            isActive={isActive}
            replayKey={replayKey}
            selectedMood={selectedMood}
          />
        </Suspense>
      </div>

      {/* Bottom flow section */}
      <div style={{
        position: 'absolute', bottom: 28, left: 60, right: 60,
        display: 'flex', gap: 40, alignItems: 'stretch',
      }}>
        {/* User card with mood buttons */}
        <div className="card" style={{ flex: 1, padding: '12px 16px' }}>
          <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic', marginBottom: 8}}>
            User selects mood:
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
            {MOODS.map((mood, i) => (
              <button
                key={mood}
                className={`btn ${selectedMood === i ? 'active' : ''}`}
                onClick={() => setSelectedMood(i)}
                style={{ fontSize: 11, padding: '3px 8px' }}
              >
                {mood}
              </button>
            ))}
          </div>
        </div>

        {/* Arrow */}
        <div style={{ display: 'flex', alignItems: 'center', color: '#9ca3af', fontSize: 20 }}>→</div>

        {/* Centroid card */}
        <div className="card card--orange" style={{ flex: 1, padding: '12px 16px', textAlign: 'center' }}>
          <p style={{ fontSize: 14, fontWeight: 'bold', color: '#e8590c'}}>Centroid</p>
          <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic'}}>
            23-dim feature vector
          </p>
        </div>

        {/* Arrow */}
        <div style={{ display: 'flex', alignItems: 'center', color: '#9ca3af', fontSize: 20 }}>→</div>

        {/* Beam Search card */}
        <div className="card" style={{ flex: 1, padding: '12px 16px', textAlign: 'center' }}>
          <p style={{ fontSize: 14, fontWeight: 'bold'}}>Beam Search Source</p>
          <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic'}}>
            feeds Module 2
          </p>
        </div>
      </div>
    </div>
  );
}
