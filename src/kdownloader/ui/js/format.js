// Number, size, time and option-label formatting. Uses the active language from i18n.js.
import { t, locale } from './i18n.js';

const KB = 1024;
const MB = KB * 1024;
const GB = MB * 1024;

function num(value, digits) {
  return new Intl.NumberFormat(locale(), { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
}

export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes < 0) return '';
  if (bytes >= GB) return `${num(bytes / GB, bytes >= 10 * GB ? 1 : 2)} GB`;
  if (bytes >= MB) return `${num(bytes / MB, bytes >= 10 * MB ? 0 : 1)} MB`;
  if (bytes >= KB) return `${num(bytes / KB, 0)} KB`;
  return `${num(bytes, 0)} B`;
}

export function formatSize(bytes, approx) {
  const s = formatBytes(bytes);
  if (!s) return '';
  return approx ? `≈ ${s}` : s;
}

export function formatSpeed(bps) {
  if (!bps || !Number.isFinite(bps) || bps <= 0) return '';
  if (bps >= MB) return `${num(bps / MB, 1)} MB/s`;
  return `${num(bps / KB, 0)} KB/s`;
}

export function formatPercent(p) {
  if (p === null || p === undefined || !Number.isFinite(p)) return '';
  const clamped = Math.max(0, Math.min(1, p));
  return new Intl.NumberFormat(locale(), { style: 'percent', maximumFractionDigits: 0 }).format(Math.floor(clamped * 100) / 100);
}

export function formatEta(sec) {
  if (sec === null || sec === undefined || !Number.isFinite(sec) || sec < 0) return '';
  if (sec < 60) return t('time.eta_sec', { n: Math.max(1, Math.ceil(sec / 5) * 5) });
  if (sec < 3600) return t('time.eta_min', { n: Math.ceil(sec / 60) });
  const hours = Math.floor(sec / 3600);
  const minutes = Math.round((sec % 3600) / 60);
  return t('time.eta_hour', { h: hours, m: minutes });
}

/** 596 -> "9:56", 3723 -> "1:02:03" */
export function formatDuration(sec) {
  if (sec === null || sec === undefined || !Number.isFinite(sec) || sec <= 0) return '';
  const s = Math.round(sec);
  const hours = Math.floor(s / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const seconds = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return hours ? `${hours}:${pad(minutes)}:${pad(seconds)}` : `${minutes}:${pad(seconds)}`;
}

/** 4980 -> "1 h 23 min" */
export function formatLongDuration(sec) {
  if (!sec || !Number.isFinite(sec) || sec <= 0) return '';
  const s = Math.round(sec);
  if (s < 60) return t('time.dur_sec', { n: s });
  const hours = Math.floor(s / 3600);
  const minutes = Math.round((s % 3600) / 60);
  if (!hours) return t('time.dur_min', { n: minutes });
  return minutes ? t('time.dur_hour_min', { h: hours, m: minutes }) : t('time.dur_hour', { h: hours });
}

/** Timestamps from Python are epoch seconds; accept milliseconds too. */
export function toMs(ts) {
  if (ts === null || ts === undefined || !Number.isFinite(ts)) return null;
  return ts > 1e12 ? ts : ts * 1000;
}

export function formatTime(ts) {
  const ms = toMs(ts);
  if (ms === null) return '';
  return new Intl.DateTimeFormat(locale(), { hour: 'numeric', minute: '2-digit' }).format(new Date(ms));
}

export function formatDate(ts) {
  const ms = toMs(ts);
  if (ms === null) return '';
  const d = new Date(ms);
  const sameYear = d.getFullYear() === new Date().getFullYear();
  return new Intl.DateTimeFormat(locale(), sameYear ? { day: 'numeric', month: 'short' } : { day: 'numeric', month: 'short', year: 'numeric' }).format(d);
}

const VCODEC = { h264: 'H.264', vp9: 'VP9', av1: 'AV1' };
const ACODEC = { aac: 'AAC', opus: 'Opus', mp3: 'MP3' };

export function codecLabel(opt) {
  if (!opt) return '';
  if (opt.kind === 'audio') return ACODEC[opt.acodec] || '';
  return VCODEC[opt.vcodec] || '';
}

/** 1080, 60 -> "1080p60" ; 2160, 30 -> "2160p" */
export function heightLabel(height, fps) {
  if (!height) return '';
  return `${height}p${fps && fps > 30 ? Math.round(fps) : ''}`;
}

/** OptionView -> "MP4 · 1080p60 · H.264" (or "MP3 · 320 kbps"-less "MP3"). */
export function optionLabel(opt) {
  if (!opt) return '';
  const parts = [String(opt.container || '').toUpperCase()];
  if (opt.kind === 'video') {
    const q = heightLabel(opt.height, opt.fps);
    if (q) parts.push(q + (opt.hdr ? ' HDR' : ''));
    const codec = codecLabel(opt);
    if (codec) parts.push(codec);
  } else if (opt.container !== 'mp3' && opt.container !== 'm4a') {
    const codec = codecLabel(opt);
    if (codec) parts.push(codec);
  }
  return parts.filter(Boolean).join(' · ');
}

/** Short name for an OptionKey ("recommended" | "max" | "mp3" | "m4a" | "h720"). */
export function optionName(key) {
  if (!key) return '';
  if (/^h\d+$/.test(key)) return t('option.height', { h: key.slice(1) });
  return t(`option.${key}.name`);
}

export function hostOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

/** Shortens a URL for chips: "youtube.com/watch?v=aqz-KE…" */
export function shortUrl(url, max = 46) {
  let s = url.replace(/^https?:\/\//, '').replace(/^www\./, '');
  if (s.length > max) s = s.slice(0, max - 1) + '…';
  return s;
}
