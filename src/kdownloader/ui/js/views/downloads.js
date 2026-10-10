// S4 downloads list, S5 success morph + confetti, S6 error cards.
// Each job has a card controller keyed by id; events patch only that card (no full re-render).
import { h, btn, clear, setText, toggle, thumbImg, prefersReducedMotion } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';
import { store, jobsSorted, isActive, FAILED_STATES } from '../store.js';
import { api } from '../api.js';
import { formatBytes, formatSpeed, formatEta, formatPercent, formatTime } from '../format.js';
import { announce, menuButton, confirmDialog } from '../ui/feedback.js';
import { burst } from '../ui/confetti.js';
import {
  cancelJob, removeJob, retryJob, copyJobDetails, openJobFile, showJobInFolder, openJobSource,
  errorActionFor, errorTexts, openHelp, showError,
} from '../actions.js';

const PP_KEYS = ['Merger', 'ExtractAudio', 'EmbedThumbnail', 'Metadata', 'VideoRemuxer', 'MoveFiles', 'FixupM3u8', 'FixupM4a', 'FFmpegMetadata', 'VideoConvertor', 'ThumbnailsConvertor', 'EmbedSubtitle'];
const AUTO_ALIASES = { update_retry: 'updating_engine', fallback_best: 'fallback', retry_network: 'retrying' };
const NOTE_ICONS = { fallback_quality: 'layers', already_downloaded: 'checkCircle', slow_site: 'gauge', cookies_used: 'cookie' };

const FILTERS = {
  all: () => true,
  active: (j) => isActive(j),
  done: (j) => j.state === 'done',
  failed: (j) => FAILED_STATES.has(j.state),
};

function qualityLabel(job) {
  const c = String(job.container || '').toUpperCase();
  if (job.height && !['MP3', 'M4A'].includes(c)) return `${c} · ${job.height}p`;
  return c;
}

export function stepLabel(job) {
  const s = job.step;
  if (!s) return t('jobs.state.downloading');
  let what;
  if (s.kind === 'video') what = job.height ? t('jobs.step.video_q', { q: `${job.height}p` }) : t('jobs.step.video');
  else if (s.kind === 'audio') what = t('jobs.step.audio');
  else what = t('jobs.step.av');
  if (s.total > 1) return t('jobs.step.n_of', { i: s.index, n: s.total, what });
  return s.kind === 'audio' ? t('jobs.step.single_audio') : t('jobs.step.single_video');
}

export function ppLabel(name, job) {
  if (name === 'ExtractAudio' && job && job.container === 'm4a') return t('jobs.pp.ExtractAudio_m4a');
  if (name && PP_KEYS.includes(name)) return t(`jobs.pp.${name}`);
  return t('jobs.pp.other');
}

function statusText(job) {
  switch (job.state) {
    case 'queued': return t('jobs.state.queued');
    case 'probing': return t('jobs.state.probing');
    case 'downloading': return stepLabel(job);
    case 'processing': return ppLabel(job.postprocessor, job);
    case 'done': {
      const parts = [job.notes && job.notes.includes('already_downloaded') ? t('jobs.state.already') : t('jobs.state.done')];
      if (job.total) parts.push(formatBytes(job.total));
      if (job.finished_at) parts.push(formatTime(job.finished_at));
      return parts.join(' · ');
    }
    case 'error': return t('jobs.state.error');
    case 'canceled': return t('jobs.state.canceled');
    case 'interrupted': return t('jobs.state.interrupted');
    default: return '';
  }
}

function statsText(job) {
  if (job.state !== 'downloading' || job.auto) return '';
  const parts = [];
  if (job.total) parts.push(t('jobs.of_size', { done: formatBytes(job.downloaded || 0), total: formatBytes(job.total) }));
  const speed = formatSpeed(job.speed);
  if (speed) parts.push(speed);
  const eta = formatEta(job.eta);
  if (eta) parts.push(eta);
  return parts.join(' · ');
}

// ---------------------------------------------------------------- card controller
function createCard(initial) {
  let job = initial;
  let actionsKey = '';
  let notesKey = '';
  let errorKey = '';
  let detailsOpen = false;

  const img = thumbImg(job.thumbnail);
  const thumb = h('div', { class: 'job-thumb' }, img, h('span', { class: 'job-thumb-fallback' }, icon(job.container === 'mp3' || job.container === 'm4a' ? 'music' : 'film', { size: 22 })));
  const title = h('div', { class: 'job-title' });
  const meta = h('div', { class: 'job-meta' });
  const notes = h('div', { class: 'job-notes' });
  const barFill = h('div', { class: 'bar-fill' });
  const barCheck = h('span', { class: 'bar-check' }, icon('check', { size: 14, strokeWidth: 3 }));
  const bar = h('div', { class: 'bar', role: 'progressbar', attrs: { 'aria-valuemin': '0', 'aria-valuemax': '100' } }, barFill, barCheck);
  const pct = h('span', { class: 'job-pct num' });
  const doneLabel = h('span', { class: 'job-done-label num' });
  const progressRow = h('div', { class: 'job-progress' }, bar, pct, doneLabel);
  const statusIcon = h('span', { class: 'job-status-icon' });
  const status = h('span', { class: 'job-status-text' });
  const stats = h('span', { class: 'job-stats num' });
  const statusRow = h('div', { class: 'job-status' }, statusIcon, status, stats);
  const autoText = h('span');
  const autoRow = h('div', { class: 'job-auto', role: 'status' }, h('span', { class: 'spinner' }), autoText);
  const errorBox = h('div', { class: 'job-error' });
  const actions = h('div', { class: 'job-actions' });
  const body = h('div', { class: 'job-body' },
    h('div', { class: 'job-head' }, title),
    h('div', { class: 'job-sub' }, meta, notes),
    progressRow, statusRow, autoRow, errorBox);
  const el = h('li', { class: 'job', tabIndex: 0, dataset: { id: job.id } }, thumb, body, actions);

  el.addEventListener('keydown', (e) => {
    if (e.target !== el) return;
    if (e.key === 'Enter' && job.state === 'done' && job.file_exists) openJobFile(job);
  });

  function renderActions() {
    const key = `${job.state}|${job.file_exists}|${job.error ? job.error.code : ''}`;
    if (key === actionsKey) return;
    actionsKey = key;
    clear(actions);
    const more = () => [
      { label: t('jobs.action.copy_details'), iconName: 'copy', onSelect: () => copyJobDetails(job) },
      { label: t('jobs.action.open_source'), iconName: 'external', onSelect: () => openJobSource(job) },
      isActive(job) ? null : { label: t('jobs.action.remove'), iconName: 'trash', onSelect: () => removeJob(job), danger: true },
    ];
    if (isActive(job)) {
      actions.append(btn({ label: t('jobs.action.cancel'), iconName: 'x', kind: 'ghost', iconOnly: true, onClick: () => cancelJob(job) }));
    } else if (job.state === 'done') {
      const open = btn({ label: t('jobs.action.open'), iconName: 'play', kind: 'soft', size: 'sm', onClick: () => openJobFile(job) });
      open.disabled = !job.file_exists;
      actions.append(open,
        btn({ label: t('jobs.action.show_folder'), iconName: 'folderOpen', kind: 'ghost', iconOnly: true, onClick: () => showJobInFolder(job), attrs: { disabled: !job.file_exists } }));
    } else if (job.state === 'canceled' || job.state === 'interrupted') {
      actions.append(btn({ label: t('jobs.action.retry'), iconName: 'retry', kind: 'soft', size: 'sm', onClick: () => retryJob(job, 'normal') }));
    }
    actions.append(menuButton(t('jobs.action.more'), more));
  }

  function renderNotes() {
    const list = Array.isArray(job.notes) ? job.notes : [];
    const fileGone = job.state === 'done' && !job.file_exists;
    const key = list.join(',') + (fileGone ? '|gone' : '');
    if (key === notesKey) return;
    notesKey = key;
    clear(notes);
    for (const n of list) {
      if (!NOTE_ICONS[n]) continue;
      notes.append(h('span', { class: ['chip', 'chip-note', `note-${n}`], attrs: { title: t(`jobs.note_hint.${n}`) } }, icon(NOTE_ICONS[n], { size: 13 }), h('span', { text: t(`jobs.note.${n}`) })));
    }
    if (fileGone) notes.append(h('span', { class: ['chip', 'chip-note', 'note-gone'] }, icon('alert', { size: 13 }), h('span', { text: t('jobs.note.file_missing') })));
  }

  function renderError() {
    const err = job.state === 'error' ? job.error : null;
    const key = err ? `${err.code}|${err.action}|${store.lang}` : '';
    if (key === errorKey) return;
    errorKey = key;
    clear(errorBox);
    if (!err) return;
    const texts = errorTexts(err);
    const action = errorActionFor(job);
    const details = h('pre', { class: 'job-error-details', text: err.details || t('jobs.no_details'), hidden: !detailsOpen, id: `det-${job.id}` });
    const toggleBtn = btn({
      label: detailsOpen ? t('jobs.action.hide_details') : t('jobs.action.details'), iconName: 'chevronDown', kind: 'ghost', size: 'sm', cls: 'details-toggle',
      attrs: { 'aria-expanded': String(detailsOpen), 'aria-controls': details.id },
      onClick: () => {
        detailsOpen = !detailsOpen;
        details.hidden = !detailsOpen;
        toggleBtn.setAttribute('aria-expanded', String(detailsOpen));
        toggleBtn.querySelector('.btn-label').textContent = detailsOpen ? t('jobs.action.hide_details') : t('jobs.action.details');
      },
    });
    const row = h('div', { class: 'job-error-actions' });
    if (action) {
      const primary = btn({ label: action.label, iconName: action.iconName, kind: 'primary', size: 'sm' });
      primary.addEventListener('click', async () => {
        primary.disabled = true;
        try { await action.run(); } finally { primary.disabled = false; }
      });
      row.append(primary);
    }
    row.append(toggleBtn,
      btn({ label: t('jobs.action.copy_details'), iconName: 'copy', kind: 'ghost', size: 'sm', onClick: () => copyJobDetails(job) }),
      btn({ label: t('jobs.action.help'), iconName: 'help', kind: 'ghost', size: 'sm', onClick: () => openHelp(err.code) }));
    errorBox.append(
      h('div', { class: 'job-error-title' }, icon('alertCircle', { size: 16 }), h('strong', { text: texts.title })),
      texts.message ? h('p', { class: 'job-error-msg', text: texts.message }) : null,
      row, details);
  }

  function update(next, prev) {
    job = next;
    const justDone = prev && prev.state !== 'done' && next.state === 'done' && store.route === 'home';
    el.dataset.state = job.state;
    setText(title, job.title || t('jobs.untitled'));
    title.title = job.title || '';
    el.setAttribute('aria-label', `${job.title || ''} · ${statusText(job)}`);
    const metaParts = [job.uploader, qualityLabel(job)].filter(Boolean);
    setText(meta, metaParts.join(' · '));

    const determinate = job.state === 'downloading' && typeof job.progress === 'number' && !job.auto;
    const pctNum = job.state === 'done' ? 100 : determinate ? Math.max(0, Math.min(100, job.progress * 100)) : 0;
    toggle(bar, 'indeterminate', job.state === 'probing' || job.state === 'processing' || (job.state === 'downloading' && typeof job.progress !== 'number'));
    toggle(bar, 'paused', Boolean(job.auto) || job.state === 'queued');
    // Keep the last known progress visible (greyed) while paused, auto-fixing or after a failure.
    const lastPct = typeof job.progress === 'number' ? Math.max(0, Math.min(100, job.progress * 100)) : 0;
    const keepLast = ['error', 'canceled', 'interrupted'].includes(job.state) || (job.state === 'downloading' && job.auto);
    barFill.style.width = `${keepLast ? lastPct : pctNum}%`;
    if (determinate || job.state === 'done') bar.setAttribute('aria-valuenow', String(Math.round(pctNum)));
    else bar.removeAttribute('aria-valuenow');
    setText(pct, determinate ? formatPercent(job.progress) : '');

    setText(status, statusText(job));
    setText(doneLabel, job.state === 'done' ? statusText(job) : '');
    setText(stats, statsText(job));
    clear(statusIcon);
    if (job.state === 'done') statusIcon.append(icon('checkCircle', { size: 14 }));
    else if (job.state === 'processing') statusIcon.append(icon('sparkles', { size: 14 }));
    else if (job.state === 'queued') statusIcon.append(icon('clock', { size: 14 }));
    else if (job.state === 'canceled' || job.state === 'interrupted') statusIcon.append(icon('x', { size: 14 }));

    const autoKey = job.auto ? AUTO_ALIASES[job.auto] || job.auto : null;
    autoRow.hidden = !autoKey;
    if (autoKey) setText(autoText, t(`jobs.auto.${['updating_engine', 'retrying', 'quiet_mode', 'fallback'].includes(autoKey) ? autoKey : 'generic'}`));

    renderNotes();
    renderError();
    renderActions();

    if (justDone) {
      el.classList.add('just-done');
      announce(t('a11y.download_done', { title: job.title }));
      setTimeout(() => {
        el.classList.remove('just-done');
        if (!prefersReducedMotion() && el.isConnected) {
          const r = bar.getBoundingClientRect();
          if (r.width && r.top > 0 && r.top < window.innerHeight) burst(r.left + r.width / 2, r.top + r.height / 2, 34);
        }
      }, 380);
    }
    if (prev && prev.state !== 'error' && job.state === 'error') announce(t('a11y.download_failed', { title: job.title }));
  }

  update(initial, null);
  return { el, update, get job() { return job; } };
}

// ---------------------------------------------------------------- section
export function createDownloads({ onEmptyChange }) {
  const cards = new Map();
  const unsubs = [];
  let lastEmpty = null;

  const chips = {};
  const chipRow = h('div', { class: 'chips', role: 'group', attrs: { 'aria-label': t('jobs.filter_label') } });
  for (const key of Object.keys(FILTERS)) {
    const count = h('span', { class: 'chip-count num' });
    const chip = h('button', {
      class: 'chip chip-filter', type: 'button', attrs: { 'aria-pressed': String(store.ui.filter === key) },
      on: { click: () => setFilter(key) },
    }, h('span', { text: t(`jobs.filter.${key}`) }), count);
    chips[key] = { chip, count };
    chipRow.append(chip);
  }
  const clearBtn = btn({ label: t('jobs.clear_finished'), iconName: 'trash', kind: 'ghost', size: 'sm', onClick: async () => {
    const res = await api.clear_finished();
    if (!res.ok) showError(res.error);
  } });
  const header = h('div', { class: 'section-head' },
    h('h2', { class: 'section-title', text: t('jobs.title') }),
    chipRow);
  const list = h('ul', { class: 'jobs', attrs: { 'aria-label': t('jobs.title') } });
  const filterEmpty = h('p', { class: 'filter-empty muted', hidden: true });
  const footText = h('span', { class: 'num' });
  const cancelAllBtn = btn({ label: t('jobs.cancel_all'), iconName: 'x', kind: 'ghost', size: 'sm', onClick: async () => {
    const yes = await confirmDialog({ title: t('jobs.cancel_all_title'), message: t('jobs.cancel_all_body'), confirmLabel: t('jobs.cancel_all_yes'), cancelLabel: t('jobs.cancel_confirm_no'), danger: true });
    if (yes) {
      const res = await api.cancel_all();
      if (!res.ok) showError(res.error);
    }
  } });
  const footer = h('div', { class: 'jobs-footer' }, footText, h('span', { class: 'spacer' }), cancelAllBtn, clearBtn);
  const el = h('section', { class: 'jobs-section', attrs: { 'aria-label': t('jobs.title') } }, header, list, filterEmpty, footer);

  function setFilter(key) {
    store.ui.filter = key;
    for (const [k, { chip }] of Object.entries(chips)) chip.setAttribute('aria-pressed', String(k === key));
    for (const card of cards.values()) card.el.hidden = !FILTERS[key](card.job);
    refreshAggregate();
  }

  let aggPending = false;
  function refreshAggregate() {
    if (aggPending) return;
    aggPending = true;
    // Timer batching (not rAF): it must keep working while the window is minimized.
    setTimeout(() => {
      aggPending = false;
      const all = [...store.jobs.values()];
      const counts = { all: all.length, active: 0, done: 0, failed: 0 };
      let remaining = 0;
      for (const j of all) {
        if (isActive(j)) {
          counts.active++;
          if (j.total && j.total > (j.downloaded || 0)) remaining += j.total - (j.downloaded || 0);
        }
        if (j.state === 'done') counts.done++;
        if (FAILED_STATES.has(j.state)) counts.failed++;
      }
      for (const [k, { count }] of Object.entries(chips)) setText(count, counts[k] ? String(counts[k]) : '');
      const parts = [t('jobs.footer_done', { done: counts.done, total: counts.all })];
      if (remaining > 0) parts.push(t('jobs.footer_left', { size: formatBytes(remaining) }));
      else if (counts.active) parts.push(t('jobs.footer_active', { count: counts.active }));
      setText(footText, parts.join(' · '));
      clearBtn.hidden = !all.some((j) => j.state === 'done' || j.state === 'canceled');
      cancelAllBtn.hidden = counts.active < 2;
      const visible = [...cards.values()].filter((c) => !c.el.hidden && !c.el.classList.contains('leaving')).length;
      filterEmpty.hidden = visible > 0 || counts.all === 0;
      if (!filterEmpty.hidden) setText(filterEmpty, t(`jobs.filter_empty.${store.ui.filter}`));
      const empty = counts.all === 0;
      el.hidden = empty;
      if (empty !== lastEmpty) {
        lastEmpty = empty;
        onEmptyChange?.(empty);
      }
    }, 40);
  }

  function insertCard(card, job, animate) {
    let before = null;
    for (const node of list.children) {
      const other = cards.get(node.dataset.id);
      if (other && (other.job.created_at || 0) < (job.created_at || 0)) {
        before = node;
        break;
      }
    }
    list.insertBefore(card.el, before);
    if (animate) {
      card.el.classList.add('enter');
      card.el.addEventListener('animationend', () => card.el.classList.remove('enter'), { once: true });
    }
  }

  function upsert(job, prev, animate = true) {
    let card = cards.get(job.id);
    if (!card) {
      card = createCard(job);
      cards.set(job.id, card);
      insertCard(card, job, animate);
    } else {
      card.update(job, prev);
    }
    card.el.hidden = !FILTERS[store.ui.filter](job);
    refreshAggregate();
  }

  function drop(id) {
    const card = cards.get(id);
    if (!card) return;
    cards.delete(id);
    const wasFocused = card.el.contains(document.activeElement);
    const next = card.el.nextElementSibling || card.el.previousElementSibling;
    card.el.classList.add('leaving');
    const done = () => card.el.remove();
    if (prefersReducedMotion()) done();
    else setTimeout(done, 200);
    if (wasFocused && next) next.focus();
    refreshAggregate();
  }

  // Initial render with a short stagger.
  jobsSorted().forEach((job, i) => {
    const card = createCard(job);
    cards.set(job.id, card);
    card.el.style.setProperty('--i', String(Math.min(i, 8)));
    card.el.classList.add('enter');
    card.el.addEventListener('animationend', () => card.el.classList.remove('enter'), { once: true });
    list.append(card.el);
    card.el.hidden = !FILTERS[store.ui.filter](job);
  });
  refreshAggregate();

  unsubs.push(store.on('job', (job, prev) => upsert(job, prev)));
  unsubs.push(store.on('job_removed', (id) => drop(id)));

  return {
    el,
    destroy() {
      unsubs.forEach((u) => u());
      cards.clear();
    },
    focusFirst() {
      list.querySelector('.job:not([hidden])')?.focus();
    },
    count: () => cards.size,
  };
}
