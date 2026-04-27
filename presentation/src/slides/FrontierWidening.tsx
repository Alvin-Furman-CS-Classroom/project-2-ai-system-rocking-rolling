import { Suspense } from 'react';
import { P5Canvas } from '@p5-wrapper/react';
import type { SlideProps } from './types';
import { frontierWideningSketch } from '../sketches/frontierWidening';

export function FrontierWidening({ isActive, replayKey }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Widening the Frontier</h2>
      <p className="slide-subtitle">ListenBrainz discovers new tracks when local similarity is exhausted</p>

      {/* Frontier widening graph */}
      <div style={{ position: 'absolute', top: 155, left: 90 }}>
        <Suspense fallback={null}>
          <P5Canvas sketch={frontierWideningSketch} isActive={isActive} replayKey={replayKey} />
        </Suspense>
      </div>

      {/* Caption */}
      <p style={{
        position: 'absolute', bottom: 28, left: 0, right: 0,
        textAlign: 'center', fontSize: 14, fontStyle: 'italic',
        color: '#9ca3af'
      }}>
        orange = forward frontier (from S) · dark = backward frontier (from D) · ringed nodes discovered via ListenBrainz · frontiers meet in the middle
      </p>
    </div>
  );
}
