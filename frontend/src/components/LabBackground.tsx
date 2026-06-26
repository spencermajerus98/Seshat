import { useEffect, useRef } from "react";
import classes from "./Unlock.module.css";

/**
 * A living, procedurally-animated backdrop of drifting, pulsing, dividing
 * "cells" joined by a faint signalling network — evoking cell culture growth.
 *
 * Pure canvas (no images/video) so it stays fully offline and lightweight.
 * Respects prefers-reduced-motion by rendering a single static frame.
 */
interface Cell {
  x: number;
  y: number;
  vx: number;
  vy: number;
  r: number;
  phase: number; // breathing offset
  color: string;
  age: number; // seconds since spawn (drives division)
}

const COLORS = ["#2dd4bf", "#34d399", "#22d3ee", "#5eead4", "#38bdf8", "#4ade80"];
const LINK_DIST = 150;

export function LabBackground() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;
    let cells: Cell[] = [];
    let raf = 0;
    let last = 0;

    const rand = (a: number, b: number) => a + Math.random() * (b - a);

    const makeCell = (x?: number, y?: number, r?: number): Cell => ({
      x: x ?? rand(0, w),
      y: y ?? rand(0, h),
      vx: rand(-12, 12),
      vy: rand(-12, 12),
      r: r ?? rand(6, 16),
      phase: rand(0, Math.PI * 2),
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
      age: 0,
    });

    const cap = () => Math.round(Math.min(52, Math.max(20, (w * h) / 42000)));

    const init = () => {
      cells = [];
      const n = cap();
      for (let i = 0; i < n; i++) cells.push(makeCell());
    };

    const resize = () => {
      w = canvas.clientWidth;
      h = canvas.clientHeight;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(h * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const drawCell = (c: Cell, t: number) => {
      const breathe = 1 + Math.sin(t * 1.4 + c.phase) * 0.12;
      const r = c.r * breathe;
      // Glow / cytoplasm.
      const g = ctx.createRadialGradient(c.x, c.y, 0, c.x, c.y, r * 2.6);
      g.addColorStop(0, c.color + "cc");
      g.addColorStop(0.45, c.color + "33");
      g.addColorStop(1, c.color + "00");
      ctx.fillStyle = g;
      ctx.beginPath();
      ctx.arc(c.x, c.y, r * 2.6, 0, Math.PI * 2);
      ctx.fill();
      // Nucleus.
      ctx.fillStyle = "rgba(255,255,255,0.85)";
      ctx.beginPath();
      ctx.arc(c.x, c.y, Math.max(1.2, r * 0.28), 0, Math.PI * 2);
      ctx.fill();
    };

    const drawLinks = () => {
      for (let i = 0; i < cells.length; i++) {
        for (let j = i + 1; j < cells.length; j++) {
          const a = cells[i];
          const b = cells[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d = Math.hypot(dx, dy);
          if (d < LINK_DIST) {
            const alpha = (1 - d / LINK_DIST) * 0.22;
            ctx.strokeStyle = `rgba(125, 230, 210, ${alpha})`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
    };

    const render = (t: number) => {
      ctx.clearRect(0, 0, w, h);
      drawLinks();
      for (const c of cells) drawCell(c, t);
    };

    const step = (dt: number) => {
      const maxCells = cap();
      const spawned: Cell[] = [];
      for (const c of cells) {
        c.x += c.vx * dt;
        c.y += c.vy * dt;
        c.age += dt;
        // Wrap softly around edges.
        if (c.x < -30) c.x = w + 30;
        if (c.x > w + 30) c.x = -30;
        if (c.y < -30) c.y = h + 30;
        if (c.y > h + 30) c.y = -30;
        // Occasional mitosis once a cell has matured — cells "grow".
        if (
          c.age > 6 &&
          cells.length + spawned.length < maxCells &&
          Math.random() < 0.06 * dt
        ) {
          c.age = 0;
          const child = makeCell(c.x + rand(-8, 8), c.y + rand(-8, 8), c.r * 0.7);
          child.color = c.color;
          spawned.push(child);
        }
      }
      if (spawned.length) cells = cells.concat(spawned);
      // Keep the population from creeping past the cap.
      if (cells.length > maxCells) cells.splice(0, cells.length - maxCells);
    };

    const frame = (now: number) => {
      const t = now / 1000;
      const dt = Math.min(0.05, last ? t - last : 0.016);
      last = t;
      step(dt);
      render(t);
      raf = requestAnimationFrame(frame);
    };

    resize();
    init();
    const onResize = () => {
      resize();
      init();
    };
    window.addEventListener("resize", onResize);

    if (reduced) {
      render(0);
    } else {
      raf = requestAnimationFrame(frame);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return <canvas ref={ref} className={classes.canvas} aria-hidden="true" />;
}
