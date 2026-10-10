// Engine component rows (yt-dlp, FFmpeg, Deno) shared by the welcome screen (S0) and Settings (S8).
import { h, btn, clear, setText, toggle } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';
import { formatBytes, formatPercent } from '../format.js';
import { api } from '../api.js';
import { showError } from '../actions.js';

export const COMPONENTS = ['ytdlp', 'ffmpeg', 'deno'];
const ICONS = { ytdlp: 'package', ffmpeg: 'film', deno: 'globe' };

export function componentStatus(name, c) {
  if (!c) return '';
  switch (c.state) {
    case 'ready':
      return c.version
        ? t(c.source === 'system' ? 'engine.status.ready_system' : 'engine.status.ready_v', { v: c.version })
        : t('engine.status.ready');
    case 'checking': return t('engine.status.checking');
    case 'downloading':
      return c.total
        ? t('engine.status.downloading_of', { pct: formatPercent(c.progress || 0), done: formatBytes(c.done || 0), total: formatBytes(c.total) })
        : t('engine.status.downloading');
    case 'installing': return t('engine.status.installing');
    case 'blocked': return t('engine.status.blocked');
    case 'error': return c.error ? t('engine.status.error_msg', { msg: c.error }) : t('engine.status.error');
    default:
      return name === 'deno' ? t('engine.status.missing_optional') : t('engine.status.missing');
  }
}

/** mode: 'onboarding' (sizes + Reintentar) or 'settings' (versions + Reparar). */
export function createComponentRows(mode) {
  const rows = {};
  const list = h('ul', { class: ['comp-list', `comp-${mode}`] });
  for (const name of COMPONENTS) {
    const iconBox = h('span', { class: 'comp-icon' });
    const size = h('span', { class: 'comp-size num' });
    const fill = h('div', { class: 'bar-fill' });
    const bar = h('div', { class: 'bar', role: 'progressbar', attrs: { 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-label': t(`engine.${name}.name`) } }, fill);
    const status = h('span', { class: 'comp-status' });
    const action = h('div', { class: 'comp-action' });
    const li = h('li', { class: 'comp', dataset: { name } },
      iconBox,
      h('div', { class: 'comp-main' },
        h('div', { class: 'comp-head' },
          h('strong', { text: t(`engine.${name}.name`) }),
          h('span', { class: 'comp-tech muted', text: t(`engine.${name}.tech`) }),
          name === 'deno' ? h('span', { class: 'badge badge-soft', text: t('engine.background') }) : null,
          size),
        mode === 'settings' ? h('p', { class: 'comp-desc muted small', text: t(`engine.${name}.desc`) }) : null,
        bar, status),
      action);
    rows[name] = { li, iconBox, size, fill, bar, status, action, key: '' };
    list.append(li);
  }

  function update(engine) {
    const comps = (engine && engine.components) || {};
    for (const name of COMPONENTS) {
      const c = comps[name] || { state: 'missing' };
      const r = rows[name];
      r.li.dataset.state = c.state;
      const working = ['checking', 'downloading', 'installing'].includes(c.state);
      const failed = c.state === 'error' || c.state === 'blocked';
      setText(r.size, c.approx_size && (mode === 'onboarding' || c.state !== 'ready') ? formatBytes(c.approx_size) : '');
      setText(r.status, componentStatus(name, c));
      toggle(r.status, 'error-text', failed);
      r.bar.hidden = !(working || (mode === 'onboarding' && c.state !== 'ready' && !failed));
      toggle(r.bar, 'indeterminate', c.state === 'checking' || c.state === 'installing' || (c.state === 'downloading' && typeof c.progress !== 'number'));
      toggle(r.bar, 'paused', c.state === 'missing');
      const pct = c.state === 'downloading' && typeof c.progress === 'number' ? c.progress * 100 : 0;
      r.fill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
      if (c.state === 'downloading' && typeof c.progress === 'number') r.bar.setAttribute('aria-valuenow', String(Math.round(pct)));
      else r.bar.removeAttribute('aria-valuenow');

      const key = `${c.state}|${mode}`;
      if (key !== r.key) {
        r.key = key;
        clear(r.iconBox);
        if (c.state === 'ready') r.iconBox.append(icon('check', { size: 18, strokeWidth: 2.6 }));
        else if (failed) r.iconBox.append(icon('alert', { size: 18 }));
        else r.iconBox.append(icon(ICONS[name], { size: 18 }));
        clear(r.action);
        if (failed) {
          r.action.append(btn({ label: t('engine.retry'), iconName: 'retry', kind: 'soft', size: 'sm', onClick: () => repair(name) }));
        } else if (mode === 'settings' && !working) {
          r.action.append(btn({ label: t('engine.repair'), iconName: 'wrench', kind: 'ghost', size: 'sm', onClick: () => repair(name) }));
        }
      }
    }
  }

  async function repair(name) {
    const res = await api.engine_repair(name);
    if (!res.ok) showError(res.error);
  }

  return { el: list, update };
}

/** Overall progress of the required components while installing (0..1) or null. */
export function engineProgress(engine) {
  if (!engine || !engine.components) return null;
  let done = 0;
  let total = 0;
  for (const name of ['ytdlp', 'ffmpeg']) {
    const c = engine.components[name];
    if (!c) continue;
    const size = c.total || c.approx_size || 0;
    total += size;
    if (c.state === 'ready') done += size;
    else if (c.state === 'downloading') done += c.done || 0;
    else if (c.state === 'installing') done += size * 0.98;
  }
  return total ? Math.min(1, done / total) : null;
}
