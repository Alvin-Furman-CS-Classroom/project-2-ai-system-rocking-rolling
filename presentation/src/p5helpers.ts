import type p5 from 'p5';
import { T } from './theme';

/** Cast p.drawingContext to 2D canvas context (we never use WebGL). */
export function ctx2d(p: p5): CanvasRenderingContext2D {
  return p.drawingContext as CanvasRenderingContext2D;
}

export interface DrawCardOpts {
  fill?: string;
  stroke?: string;
  sw?: number;
  radius?: number;
}

export interface DrawTextOpts {
  font?: string;
  size?: number;
  bold?: boolean;
  italic?: boolean;
  color?: string;
  align?: string;
  vAlign?: string;
}

export interface ThemeHelpers {
  drawCard(x: number, y: number, w: number, h: number, opts?: DrawCardOpts): void;
  drawTitle(txt: string, y?: number): void;
  drawSubtitle(txt: string, y?: number): void;
  drawText(txt: string, x: number, y: number, opts?: DrawTextOpts): void;
  drawBar(x: number, y: number, w: number, h: number, frac: number, color?: string): void;
  drawButton(x: number, y: number, w: number, h: number, label: string, isActive?: boolean, isHover?: boolean): void;
  easeInOut(t: number): number;
  easeOut(t: number): number;
  inRect(mx: number, my: number, x: number, y: number, w: number, h: number): boolean;
}

export function createThemeHelpers(p: p5): ThemeHelpers {
  function drawCard(x: number, y: number, w: number, h: number, opts: DrawCardOpts = {}) {
    p.push();
    p.fill(opts.fill ?? T.SURFACE);
    p.stroke(opts.stroke ?? T.BORDER);
    p.strokeWeight(opts.sw ?? 1.5);
    p.rect(x, y, w, h, opts.radius ?? 6);
    p.pop();
  }

  function drawTitle(txt: string, y = 60) {
    p.push();
    p.textFont('Noto Serif');
    p.textSize(42);
    p.textStyle(p.BOLD);
    p.fill(T.TEXT);
    p.noStroke();
    p.textAlign(p.LEFT, p.TOP);
    p.text(txt, T.MARGIN, y);
    p.pop();
  }

  function drawSubtitle(txt: string, y = 115) {
    p.push();
    p.textFont('Noto Serif');
    p.textStyle(p.ITALIC);
    p.textSize(20);
    p.fill(T.MUTED);
    p.noStroke();
    p.textAlign(p.LEFT, p.TOP);
    p.text(txt, T.MARGIN, y);
    p.pop();
  }

  function drawText(txt: string, x: number, y: number, opts: DrawTextOpts = {}) {
    p.push();
    p.textFont(opts.font ?? 'Noto Serif');
    p.textSize(opts.size ?? 18);
    if (opts.bold) p.textStyle(p.BOLD);
    else if (opts.italic) p.textStyle(p.ITALIC);
    p.fill(opts.color ?? T.TEXT);
    p.noStroke();
    const ha = opts.align === 'center' ? p.CENTER
      : opts.align === 'right' ? p.RIGHT : p.LEFT;
    const va = opts.vAlign === 'center' ? p.CENTER
      : opts.vAlign === 'bottom' ? p.BOTTOM
      : opts.vAlign === 'baseline' ? p.BASELINE : p.TOP;
    p.textAlign(ha, va);
    p.text(txt, x, y);
    p.pop();
  }

  function drawBar(x: number, y: number, w: number, h: number, frac: number, color = T.ORANGE) {
    p.push();
    p.noStroke();
    p.fill(T.SURFACE);
    p.rect(x, y, w, h, 3);
    p.stroke(T.BORDER);
    p.strokeWeight(1);
    p.noFill();
    p.rect(x, y, w, h, 3);
    p.noStroke();
    p.fill(color);
    if (frac > 0) p.rect(x, y, w * frac, h, 3);
    p.pop();
  }

  function drawButton(x: number, y: number, w: number, h: number, label: string, isActive = false, isHover = false) {
    p.push();
    p.noStroke();
    if (isActive) p.fill(T.ORANGE_L);
    else if (isHover) p.fill(T.SURFACE);
    else p.fill(255);
    p.rect(x, y, w, h, 5);
    p.stroke(isActive ? T.ORANGE : T.BORDER);
    p.strokeWeight(isActive ? 2 : 1.5);
    p.noFill();
    p.rect(x, y, w, h, 5);
    p.noStroke();
    p.fill(isActive ? T.ORANGE : T.TEXT);
    p.textFont('Noto Serif');
    p.textSize(14);
    p.textStyle(isActive ? p.BOLD : p.NORMAL);
    p.textAlign(p.CENTER, p.CENTER);
    p.text(label, x + w / 2, y + h / 2);
    p.pop();
  }

  const easeInOut = (t: number) => t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
  const easeOut   = (t: number) => 1 - Math.pow(1 - t, 3);
  const inRect    = (mx: number, my: number, x: number, y: number, w: number, h: number) =>
    mx >= x && mx <= x + w && my >= y && my <= y + h;

  return { drawCard, drawTitle, drawSubtitle, drawText, drawBar, drawButton, easeInOut, easeOut, inRect };
}
