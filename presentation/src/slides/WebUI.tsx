import type { SlideProps } from './types';

const TRACKS = [
  { num: 1, name: 'Girls Just Wanna Have Fun', artist: 'Cyndi Lauper',  pct: 87 },
  { num: 2, name: 'Walking on Sunshine',        artist: 'Katrina & The Waves', pct: 82 },
  { num: 3, name: "Don't Stop Me Now",          artist: 'Queen',         pct: 76 },
  { num: 4, name: 'Under Pressure',             artist: 'Queen & Bowie', pct: 71 },
  { num: 5, name: 'Comfortably Numb',           artist: 'Pink Floyd',    pct: -1 },
] as const;

export function WebUI({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">The Experience</h2>
      <p className="slide-subtitle">React + TypeScript Web Interface</p>

      {/* Browser frame */}
      <div style={{
        position: 'absolute', top: 155, left: 60, right: 60, bottom: 40,
        background: '#fafafa', border: '1.5px solid #e0e0e0', borderRadius: 8,
        overflow: 'hidden'
      }}>
        {/* Title bar */}
        <div style={{
          background: '#eeeeee', height: 32,
          display: 'flex', alignItems: 'center', padding: '0 14px',
          borderBottom: '1px solid #e0e0e0', flexShrink: 0,
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: '#ff5f56' }} />
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: '#ffbd2e' }} />
            <div style={{ width: 9, height: 9, borderRadius: '50%', background: '#27c93f' }} />
          </div>
          <div style={{ flex: 1, textAlign: 'center', fontSize: 12, color: '#9ca3af' }}>
            localhost:5173
          </div>
        </div>

        {/* Content */}
        <div style={{ padding: '20px 24px' }}>
          {/* Source / Dest pickers */}
          <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic', marginBottom: 8 }}>Source Track</p>
              <div className="card" style={{ padding: '10px 16px', background: '#fff' }}>
                <p style={{ fontSize: 17, fontWeight: 'bold' }}>Girls Just Wanna Have Fun</p>
                <p style={{ fontSize: 13, color: '#9ca3af' }}>Cyndi Lauper</p>
              </div>
            </div>
            <div style={{ flex: 1 }}>
              <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic', marginBottom: 8 }}>Destination Track</p>
              <div className="card" style={{ padding: '10px 16px', background: '#fff' }}>
                <p style={{ fontSize: 17, fontWeight: 'bold' }}>Comfortably Numb</p>
                <p style={{ fontSize: 13, color: '#9ca3af' }}>Pink Floyd</p>
              </div>
            </div>
          </div>

          {/* Generate button */}
          <div style={{ textAlign: 'center', marginBottom: 20 }}>
            <button style={{
              background: '#e8590c', color: '#fff',
              border: 'none', borderRadius: 5, padding: '10px 40px',
              fontSize: 14, fontWeight: 'bold', cursor: 'pointer',

            }}>
              Generate Playlist
            </button>
          </div>

          {/* Track list */}
          {TRACKS.map((t, i) => (
            <div
              key={t.num}
              className="animate-item"
              style={{
                display: 'flex', alignItems: 'center',
                padding: '8px 12px', borderRadius: 4, marginBottom: 4,
                background: i % 2 === 0 ? '#fff' : '#fafafa',
                border: '0.5px solid #e0e0e0',
                animationDelay: `${0.1 + i * 0.1}s`,
              }}
            >
              <span style={{ width: 28, fontWeight: 'bold', color: '#e8590c', textAlign: 'center', fontSize: 15, flexShrink: 0 }}>
                {t.num}
              </span>
              <span style={{ flex: 1, fontWeight: 'bold', fontSize: 14 }}>{t.name}</span>
              <span style={{ width: 180, fontSize: 13, color: '#9ca3af' }}>{t.artist}</span>
              {t.pct >= 0 ? (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div style={{ width: 110, height: 10, background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 3, overflow: 'hidden' }}>
                    <div style={{ width: `${t.pct}%`, height: '100%', background: t.pct > 75 ? '#e8590c' : '#1a1a1a', borderRadius: 3 }} />
                  </div>
                  <span style={{ fontSize: 13, fontWeight: 'bold', color: t.pct > 75 ? '#e8590c' : '#1a1a1a', width: 36, textAlign: 'right' }}>
                    {t.pct}%
                  </span>
                </div>
              ) : (
                <span style={{ fontSize: 12, fontWeight: 'bold', color: '#9ca3af', width: 52, textAlign: 'right' }}>DEST</span>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
