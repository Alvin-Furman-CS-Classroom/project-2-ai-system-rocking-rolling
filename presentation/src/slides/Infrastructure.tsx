import type { SlideProps } from './types';

const SOURCES = [
  {
    name: 'MusicBrainz',
    stats: ['38M recordings', '2.8M artists', '6.8M genre tags'],
    badge: 'Postgres Mirror',
    orange: true,
  },
  {
    name: 'AcousticBrainz',
    stats: ['~2M recordings', '60+ descriptors', 'MFCCs / spectral'],
    badge: 'Archived API',
    orange: false,
  },
  {
    name: 'ListenBrainz',
    stats: ['Live similarity graph', '4 algorithms merged', 'User tags & listens'],
    badge: 'Live API',
    orange: false,
  },
] as const;

export function Infrastructure({ isActive }: SlideProps) {
  return (
    <div className={`slide ${isActive ? 'active' : ''}`}>
      <h2 className="slide-title">38 Million Recordings</h2>
      <p className="slide-subtitle">Open-Source Database Infrastructure</p>

      {/* Source cards */}
      <div style={{ position: 'absolute', top: 155, left: 60, right: 60, display: 'flex', gap: 30 }}>
        {SOURCES.map((s, i) => (
          <div
            key={i}
            className={`card animate-item ${s.orange ? 'card--orange' : ''}`}
            style={{ flex: 1, animationDelay: `${i * 0.2}s` }}
          >
            <h3 style={{ color: s.orange ? '#e8590c' : '#1a1a1a', marginBottom: 12 }}>{s.name}</h3>
            {s.stats.map(stat => (
              <p key={stat} style={{ fontSize: 15, marginBottom: 6 }}>• {stat}</p>
            ))}
            <div style={{
              marginTop: 16, display: 'inline-block',
              background: s.orange ? 'rgba(232,89,12,0.12)' : 'rgba(156,163,175,0.15)',
              borderRadius: 4, padding: '4px 12px',
              fontSize: 12, fontWeight: 'bold',
              color: s.orange ? '#e8590c' : '#9ca3af',

            }}>
              {s.badge}
            </div>
          </div>
        ))}
      </div>

      {/* Speed comparison */}
      <div style={{ position: 'absolute', top: 434, left: 60, right: 60}}>
        <p style={{ fontSize: 17, fontWeight: 'bold', color: '#9ca3af', marginBottom: 4 }}>
          Query Speed Comparison
        </p>
        <p style={{ fontSize: 13, color: '#9ca3af', fontStyle: 'italic', marginBottom: 20 }}>
          per recording lookup against the MusicBrainz catalog
        </p>

        {/* Postgres bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
          <span style={{ width: 260, textAlign: 'right', fontSize: 14, fontWeight: 'bold', color: '#e8590c', flexShrink: 0 }}>
            Self-hosted Postgres Mirror
          </span>
          <div style={{ background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 3, height: 26, flex: 1, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: '4%', background: '#e8590c', borderRadius: 3 }} />
          </div>
          <span style={{ fontSize: 15, fontWeight: 'bold', color: '#e8590c', width: 80, flexShrink: 0 }}>~2 ms</span>
        </div>

        {/* REST API bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
          <span style={{ width: 260, textAlign: 'right', fontSize: 14, fontWeight: 'bold', flexShrink: 0 }}>
            Public MusicBrainz REST API
          </span>
          <div style={{ background: '#f5f5f5', border: '1px solid #e0e0e0', borderRadius: 3, height: 26, flex: 1, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: '100%', background: '#1a1a1a', borderRadius: 3 }} />
          </div>
          <span style={{ fontSize: 15, fontWeight: 'bold', width: 80, flexShrink: 0 }}>~1000 ms</span>
        </div>

        <p style={{ textAlign: 'right', fontSize: 19, fontWeight: 'bold', color: '#e8590c', marginTop: 8 }}>
          500× faster — no rate limits
        </p>
      </div>
    </div>
  );
}
