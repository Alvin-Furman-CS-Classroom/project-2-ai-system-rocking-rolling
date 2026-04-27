import { Suspense } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { compatibilitySketch } from '../sketches/compatibility';

export function Compatibility({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Track Compatibility</h2>
      <p className="slide-subtitle">Per-dimension weighted similarity scoring</p>

      {/* Track name labels */}
      <div style={{ position: 'absolute', top: 148, left: 60, right: 60, display: 'flex', justifyContent: 'space-between' }}>
        <div className="card card--orange" style={{ padding: '8px 20px' }}>
          <span style={{ fontWeight: 'bold', color: '#e8590c', fontSize: 15 }}>Girls Just Wanna Have Fun</span>
          <span style={{ color: '#9ca3af', fontSize: 13, marginLeft: 10 }}>Cyndi Lauper</span>
        </div>
        <div className="card" style={{ padding: '8px 20px' }}>
          <span style={{ fontWeight: 'bold', fontSize: 15 }}>Comfortably Numb</span>
          <span style={{ color: '#9ca3af', fontSize: 13, marginLeft: 10 }}>Pink Floyd</span>
        </div>
      </div>

      {/* Compatibility bars + score */}
      <div style={{ position: 'absolute', top: 210, left: 60 }}>
        <Suspense fallback={null}>
          <P5Canvas sketch={compatibilitySketch} isActive={isActive} replayKey={replayKey} />
        </Suspense>
      </div>
    </div>
  );
}
