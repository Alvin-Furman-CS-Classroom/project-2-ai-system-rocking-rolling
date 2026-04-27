import { Suspense } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { beamSearchSketch } from '../sketches/beamSearch';

export function BeamSearch({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Finding the Path</h2>
      <p className="slide-subtitle">Bidirectional Beam Search with A* heuristic</p>

      {/* Beam search graph */}
      <div style={{ position: 'absolute', top: 155, left: 90 }}>
        <Suspense fallback={null}>
          <P5Canvas sketch={beamSearchSketch} isActive={isActive} replayKey={replayKey} />
        </Suspense>
      </div>

      {/* Caption */}
      <p style={{
        position: 'absolute', bottom: 28, left: 0, right: 0,
        textAlign: 'center', fontSize: 14, fontStyle: 'italic',
        color: '#9ca3af'
      }}>
        S = source track · D = destination track · orange = forward frontier · white = backward frontier
      </p>
    </div>
  );
}
