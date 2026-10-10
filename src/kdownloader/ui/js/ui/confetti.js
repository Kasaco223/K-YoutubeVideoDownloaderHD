// Light micro-confetti (canvas, <= 40 particles, ~1 s). Skipped entirely with reduced motion.
import { prefersReducedMotion } from '../dom.js';

const COLORS = ['#6366F1', '#8B5CF6', '#F97362', '#34D399', '#FBBF24', '#A5B4FC'];
let particles = [];
let running = false;

export function burst(x, y, count = 32) {
  if (prefersReducedMotion()) return;
  const canvas = document.getElementById('confetti');
  if (!canvas) return;
  const n = Math.min(40, count);
  for (let i = 0; i < n; i++) {
    const angle = -Math.PI / 2 + (Math.random() - 0.5) * Math.PI * 1.1;
    const speed = 3 + Math.random() * 4.5;
    particles.push({
      x, y,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      size: 3 + Math.random() * 3.5,
      rot: Math.random() * Math.PI,
      vr: (Math.random() - 0.5) * 0.4,
      color: COLORS[i % COLORS.length],
      life: 0,
      ttl: 55 + Math.random() * 25,
      shape: i % 3,
    });
  }
  if (particles.length > 40) particles = particles.slice(-40);
  if (!running) start(canvas);
}

function start(canvas) {
  running = true;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const resize = () => {
    canvas.width = Math.round(window.innerWidth * dpr);
    canvas.height = Math.round(window.innerHeight * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  };
  resize();
  canvas.classList.add('active');
  const frame = () => {
    ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
    particles = particles.filter((p) => p.life < p.ttl);
    for (const p of particles) {
      p.life += 1;
      p.vy += 0.18;
      p.vx *= 0.985;
      p.x += p.vx;
      p.y += p.vy;
      p.rot += p.vr;
      ctx.save();
      ctx.globalAlpha = Math.max(0, 1 - p.life / p.ttl);
      ctx.translate(p.x, p.y);
      ctx.rotate(p.rot);
      ctx.fillStyle = p.color;
      if (p.shape === 0) ctx.fillRect(-p.size / 2, -p.size / 4, p.size, p.size / 2);
      else if (p.shape === 1) {
        ctx.beginPath();
        ctx.arc(0, 0, p.size / 2.4, 0, Math.PI * 2);
        ctx.fill();
      } else ctx.fillRect(-p.size / 3, -p.size / 3, p.size / 1.5, p.size / 1.5);
      ctx.restore();
    }
    if (particles.length) requestAnimationFrame(frame);
    else {
      running = false;
      ctx.clearRect(0, 0, window.innerWidth, window.innerHeight);
      canvas.classList.remove('active');
    }
  };
  requestAnimationFrame(frame);
}
