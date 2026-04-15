import type { P5CanvasInstance, Sketch, SketchProps } from '@p5-wrapper/react';
import { T } from '../theme';

type Props = SketchProps & { isActive: boolean; replayKey: number };

export const waveformSketch: Sketch<Props> = (p: P5CanvasInstance<Props>) => {
  let localFrame = 0;
  let wasActive = false;
  let lastReplayKey = 0;

  function enter() { localFrame = 0; }

  p.setup = () => {
    p.createCanvas(1280, 140);
    p.textFont('Noto Serif');
    enter();
  };

  p.updateWithProps = (props: Props) => {
    const replay = props.isActive && props.replayKey !== lastReplayKey;
    if ((props.isActive && !wasActive) || replay) { enter(); p.loop(); }
    else if (!props.isActive && wasActive) { p.noLoop(); }
    wasActive = props.isActive;
    lastReplayKey = props.replayKey;
  };

  p.draw = () => {
    p.background(T.BG);
    localFrame++;

    // Animated waveform bars
    p.noStroke();
    for (let i = 0; i < 80; i++) {
      const x = 50 + i * (1280 - 100) / 80;
      const baseH = 8 + 35 * Math.abs(Math.sin(i * 0.4 + localFrame * 0.04));
      const opacity = 0.08 + 0.08 * Math.sin(i * 0.2 + localFrame * 0.05);
      p.fill(232, 89, 12, opacity * 255);
      p.rect(x, 140 - baseH, 8, baseH, 2);
    }
  };

};
