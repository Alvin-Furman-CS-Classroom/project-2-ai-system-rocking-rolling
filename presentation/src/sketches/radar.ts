import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import { T } from '../theme';

export const DIMS = ['Key','Tempo','Energy','Loudness','Mood','Timbre','Genre','Tags','Popularity','Artist','Era'];

export const SONGS = [
  { name: 'Girls Just Wanna Have Fun', artist: 'Cyndi Lauper',  color: '#e91e8c',
    vals: [0.75,0.68,0.75,0.82,0.90,0.55,0.70,0.65,0.80,0.50,0.60] },
  { name: 'Comfortably Numb',          artist: 'Pink Floyd',    color: '#7c3aed',
    vals: [0.60,0.45,0.60,0.70,0.35,0.80,0.55,0.50,0.75,0.65,0.55] },
  { name: 'Symphony No. 35',           artist: 'Mozart',        color: '#d97706',
    vals: [0.85,0.55,0.40,0.50,0.60,0.90,0.95,0.30,0.40,0.70,0.20] },
  { name: 'Bohemian Rhapsody',         artist: 'Queen',         color: '#dc2626',
    vals: [0.70,0.50,0.80,0.85,0.75,0.70,0.65,0.80,0.95,0.55,0.50] },
];

type Props = SketchProps & { isActive: boolean; replayKey: number; selectedSong: number };

export const radarSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let animVals = [...SONGS[0].vals];
  let targetSong = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  const cx = 270, cy = 240, R = 200;
  const n = DIMS.length;
  const angle = (i: number) => (i / n) * Math.PI * 2 - Math.PI / 2;

  function enter() {
    animVals = [...SONGS[targetSong].vals];
  }

  p.setup = () => {
    p.createCanvas(540, 480);
    p.textFont('Noto Serif');
    enter();
  };

  p.updateWithProps = (props: Props) => {
    targetSong = props.selectedSong ?? 0;
    const replay = props.isActive && props.replayKey !== lastReplayKey;
    if ((props.isActive && !wasActive) || replay) { enter(); p.loop(); }
    else if (!props.isActive && wasActive) { p.noLoop(); }
    wasActive = props.isActive;
    lastReplayKey = props.replayKey;
  };

  p.draw = () => {
    p.background(T.BG);

    const target = SONGS[targetSong].vals;
    for (let i = 0; i < n; i++) {
      animVals[i] += (target[i] - animVals[i]) * 0.12;
    }

    p.push();

    // Grid rings
    p.noFill();
    p.stroke(T.BORDER);
    p.strokeWeight(0.8);
    for (const frac of [0.25, 0.5, 0.75, 1.0]) {
      p.beginShape();
      for (let i = 0; i < n; i++) {
        const a = angle(i);
        p.vertex(cx + R * frac * Math.cos(a), cy + R * frac * Math.sin(a));
      }
      p.endShape(p.CLOSE);
    }

    // Axis lines
    p.stroke(T.BORDER);
    p.strokeWeight(0.5);
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      p.line(cx, cy, cx + R * Math.cos(a), cy + R * Math.sin(a));
    }

    // Data polygon — colored by song
    const col = p.color(SONGS[targetSong].color);
    p.fill(p.red(col), p.green(col), p.blue(col), 50);
    p.stroke(col);
    p.strokeWeight(2);
    p.beginShape();
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      p.vertex(cx + R * animVals[i] * Math.cos(a), cy + R * animVals[i] * Math.sin(a));
    }
    p.endShape(p.CLOSE);

    // Dots
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      p.noStroke();
      p.fill(col);
      p.circle(cx + R * animVals[i] * Math.cos(a), cy + R * animVals[i] * Math.sin(a), 9);
    }

    // Labels
    p.textFont('Noto Serif');
    p.textSize(13);
    p.textAlign(p.CENTER, p.CENTER);
    p.noStroke();
    for (let i = 0; i < n; i++) {
      const a = angle(i);
      const lx = cx + (R + 28) * Math.cos(a);
      const ly = cy + (R + 28) * Math.sin(a);
      p.fill(T.TEXT);
      p.text(DIMS[i], lx, ly);
    }

    p.pop();
  };
};
