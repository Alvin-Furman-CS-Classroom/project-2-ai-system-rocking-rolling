import { Suspense } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { architectureSketch } from '../sketches/architecture';

export function Architecture({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Architecture</h2>
      <p className="slide-subtitle">Four modules, one open-source stack</p>

      {/* Architecture diagram */}
      <div style={{ position: 'absolute', top: 155, left: 60 }}>
        <Suspense fallback={null}>
          <P5Canvas sketch={architectureSketch} isActive={isActive} replayKey={replayKey} />
        </Suspense>
      </div>
    </div>
  );
}
