import { useMemo } from 'react';
import katex from 'katex';
import 'katex/dist/katex.min.css';
import type { SlideProps } from './types';

const DIMS = ['Key', 'Tempo', 'Energy', 'Loudness', 'Mood', 'Timbre'] as const;
const BEFORE = [0.15, 0.20, 0.15, 0.05, 0.15, 0.15] as const;
const AFTER  = [0.12, 0.25, 0.20, 0.04, 0.10, 0.18] as const;
const MAX_W = 0.30;

function WeightBar({ value, maxW, color, isActive }: { value: number; maxW: number; color: string; isActive: boolean }) {
  return (
    <div style={{ background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 3, height: 18, flex: 1, overflow: 'hidden' }}>
      <div style={{
        height: '100%', borderRadius: 3, background: color,
        width: isActive ? `${(value / maxW) * 100}%` : '0%',
        transition: 'width 0.6s ease-out',
      }} />
    </div>
  );
}

export function Preferences({ isActive }: SlideProps) {
  const formulaHTML = useMemo(() =>
    katex.renderToString(
      'w_{t+1} = \\alpha \\cdot w_{\\text{feedback}} + (1 - \\alpha) \\cdot w_t',
      { throwOnError: false, displayMode: true }
    ), []);

  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">Learning Your Taste</h2>
      <p className="slide-subtitle">Exponential Moving Average preference adaptation</p>

      {/* Two-column weight comparison */}
      <div style={{ position: 'absolute', top: 155, left: 60, right: 60, display: 'flex', gap: 60 }}>
        {/* Default weights column */}
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 17, fontWeight: 'bold', color: '#9ca3af', marginBottom: 16}}>
            Default Weights
          </p>
          {DIMS.map((dim, i) => (
            <div key={dim} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14}}>
              <span style={{ width: 80, textAlign: 'right', fontSize: 15, color: '#9ca3af' }}>{dim}</span>
              <WeightBar value={BEFORE[i]} maxW={MAX_W} color={i % 2 === 0 ? '#e8590c' : '#1a1a1a'} isActive={isActive} />
              <span style={{ width: 48, fontSize: 13, fontWeight: 'bold' }}>{Math.round(BEFORE[i] * 100)}%</span>
            </div>
          ))}
        </div>

        {/* After feedback column */}
        <div style={{ flex: 1 }}>
          <p style={{ fontSize: 17, fontWeight: 'bold', color: '#e8590c', marginBottom: 16}}>
            After Feedback (4/5)
          </p>
          {DIMS.map((dim, i) => {
            const diff = AFTER[i] - BEFORE[i];
            const arrow = diff > 0.005 ? ' ↑' : diff < -0.005 ? ' ↓' : '';
            const diffColor = diff > 0 ? '#e8590c' : diff < 0 ? '#9ca3af' : '#1a1a1a';
            return (
              <div key={dim} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14}}>
                <span style={{ width: 80, textAlign: 'right', fontSize: 15, color: '#9ca3af' }}>{dim}</span>
                <WeightBar value={AFTER[i]} maxW={MAX_W} color={i % 2 === 0 ? '#e8590c' : '#1a1a1a'} isActive={isActive} />
                <span style={{ width: 64, fontSize: 13, fontWeight: 'bold', color: diffColor }}>
                  {Math.round(AFTER[i] * 100)}%{arrow}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Feedback card */}
      <div className="card card--orange" style={{
        position: 'absolute', bottom: 120, left: '50%', transform: 'translateX(-50%)',
        width: 720, padding: '16px 24px',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10}}>
          <span style={{ fontSize: 17, fontWeight: 'bold', color: '#e8590c' }}>User Feedback</span>
          <span style={{ color: '#e8590c', fontSize: 20, letterSpacing: 2 }}>★★★★☆</span>
          <span style={{ fontSize: 15, fontWeight: 'bold', color: '#e8590c' }}>4 / 5</span>
        </div>
        <p style={{ fontSize: 17, fontStyle: 'italic', marginBottom: 8 }}>
          "Loved the tempo flow — the mood felt a bit off though."
        </p>
        <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic'}}>
          Backend: EMA learning + JSON profile (~/.waveguide/user_profile.json)
        </p>
      </div>

      {/* KaTeX formula */}
      <div
        style={{
          position: 'absolute', bottom: 28, left: 0, right: 0,
          textAlign: 'center', fontSize: 16,
        }}
        dangerouslySetInnerHTML={{ __html: formulaHTML }}
      />
    </div>
  );
}
