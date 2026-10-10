// Shared user actions: settings, folders, cookies, error-action buttons, copy helpers, navigation.
import { api } from './api.js';
import { store, setSettings, isActive } from './store.js';
import { t, getLang } from './i18n.js';
import { h } from './dom.js';
import { toast, confirmDialog, openModal } from './ui/feedback.js';
import { formatPercent } from './format.js';

// ---------------------------------------------------------------- navigation
export const ROUTES = ['home', 'history', 'settings', 'help'];

export function navigate(route, opts = {}) {
  if (!ROUTES.includes(route) && route !== 'welcome') return;
  const changed = store.route !== route;
  store.route = route;
  if (changed || opts.force) store.emit('route', route, opts);
}

// ---------------------------------------------------------------- error texts
/** Localized {title, message, help} for an ErrorView, following the active language. */
export function errorTexts(err) {
  if (!err) return { title: t('errors.unknown_title'), message: '', help: '' };
  const local = err.texts && err.texts[getLang()];
  return {
    title: (local && local.title) || err.title || t('errors.unknown_title'),
    message: (local && local.message) || err.message || '',
    help: (local && local.help) || '',
  };
}

export function showError(err, fallbackKey = 'errors.generic') {
  const e = errorTexts(err);
  toast(e.title && e.title !== t('errors.unknown_title') ? `${e.title}. ${e.message}`.trim() : t(fallbackKey), { kind: 'error', timeout: 6000 });
}

// ---------------------------------------------------------------- clipboard (writing only)
export async function copyText(text, successKey = 'common.copied') {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const area = h('textarea', { value: text, attrs: { readonly: true, 'aria-hidden': 'true' }, class: 'sr-only' });
    document.body.appendChild(area);
    area.select();
    try {
      document.execCommand('copy');
    } finally {
      area.remove();
    }
  }
  toast(t(successKey), { kind: 'success', timeout: 2200 });
}

// ---------------------------------------------------------------- settings
export async function saveSettings(patch, { silent = false } = {}) {
  const res = await api.save_settings(patch);
  if (res.ok) {
    if (res.settings) setSettings(res.settings);
    return true;
  }
  if (!silent) showError(res.error, 'settings.save_failed');
  // Restore the real values in every control.
  if (store.settings) store.emit('settings', store.settings);
  return false;
}

export async function chooseFolder() {
  const res = await api.choose_folder();
  if (res.ok && res.settings) {
    setSettings(res.settings);
    return true;
  }
  if (!res.ok && res.error && res.error.code !== 'canceled') showError(res.error);
  return false;
}

/** Warns about account risk, then asks Python to open the file picker. */
export async function chooseCookiesFile() {
  const body = h('div', { class: 'stack-2' },
    h('p', { text: t('cookies.warning_1') }),
    h('p', { text: t('cookies.warning_2') }),
    h('p', { class: 'muted', text: t('cookies.warning_3') }));
  const goOn = await openModal({
    title: t('cookies.warning_title'),
    body,
    iconName: 'cookie',
    tone: 'warning',
    dismissValue: false,
    actions: [
      { label: t('common.cancel'), kind: 'secondary', value: false },
      { label: t('cookies.choose_file'), kind: 'primary', value: true, iconName: 'folderOpen' },
    ],
  });
  if (!goOn) return false;
  const res = await api.choose_cookies_file();
  if (res.ok && res.settings) {
    setSettings(res.settings);
    toast(t('cookies.saved'), { kind: 'success' });
    return true;
  }
  if (!res.ok && res.error && res.error.code !== 'canceled') showError(res.error);
  return false;
}

export async function clearCookiesFile() {
  const res = await api.clear_cookies_file();
  if (res.ok && res.settings) setSettings(res.settings);
  else if (!res.ok) showError(res.error);
}

// ---------------------------------------------------------------- pages / help
export function openHelp(code) {
  api.open_help(code || 'unknown').then((res) => { if (!res.ok) showError(res.error); });
}

export function openPage(key) {
  api.open_page(key).then((res) => { if (!res.ok) showError(res.error); });
}

// ---------------------------------------------------------------- jobs
export async function cancelJob(job) {
  if (!job) return;
  if (typeof job.progress === 'number' && job.progress > 0.5 && job.state === 'downloading') {
    const yes = await confirmDialog({
      title: t('jobs.cancel_confirm_title'),
      message: t('jobs.cancel_confirm_body', { pct: formatPercent(job.progress) }),
      confirmLabel: t('jobs.cancel_confirm_yes'),
      cancelLabel: t('jobs.cancel_confirm_no'),
      danger: true,
    });
    if (!yes) return;
  }
  const res = await api.cancel(job.id);
  if (!res.ok) showError(res.error);
}

export async function removeJob(job) {
  if (!job) return;
  if (isActive(job)) return cancelJob(job);
  const res = await api.remove(job.id);
  if (!res.ok) showError(res.error);
}

export async function retryJob(job, mode = 'normal') {
  const res = await api.retry(job.id, mode);
  if (!res.ok) showError(res.error);
  return res.ok;
}

export async function copyJobDetails(job) {
  const res = await api.copy_details(job.id);
  if (res.ok && typeof res.text === 'string') await copyText(res.text, 'jobs.details_copied');
  else if (job.error && job.error.details) await copyText(job.error.details, 'jobs.details_copied');
  else showError(res.error);
}

export async function openJobFile(job) {
  const res = await api.open_file(job.id);
  if (!res.ok) showError(res.error, 'jobs.open_failed');
}

export async function showJobInFolder(job) {
  const res = await api.show_in_folder(job.id);
  if (!res.ok) showError(res.error, 'jobs.open_failed');
}

export async function openJobSource(job) {
  const res = await api.open_source(job.id);
  if (!res.ok) showError(res.error);
}

/** Error action -> {label, iconName, run}. Mapping from docs/architecture.md §6. */
export function errorActionFor(job) {
  const action = job.error && job.error.action;
  switch (action) {
    case 'update_retry':
      return {
        label: t('erroraction.update_retry'), iconName: 'refresh',
        run: async () => {
          const up = await api.engine_update(true);
          if (!up.ok) return showError(up.error);
          toast(t('engine.updating_toast'), { kind: 'info' });
          await retryJob(job, 'normal');
        },
      };
    case 'retry':
      return { label: t('erroraction.retry'), iconName: 'retry', run: () => retryJob(job, 'normal') };
    case 'retry_later':
      return {
        label: t('erroraction.retry_later'), iconName: 'clock',
        run: async () => {
          if (await retryJob(job, 'normal')) toast(t('erroraction.retry_later_toast'), { kind: 'info' });
        },
      };
    case 'choose_quality':
      return { label: t('erroraction.choose_quality'), iconName: 'layers', run: () => retryJob(job, 'best') };
    case 'cookies':
      return {
        label: t('erroraction.cookies'), iconName: 'cookie',
        run: async () => {
          if (await chooseCookiesFile()) await retryJob(job, 'with_cookies');
        },
      };
    case 'choose_folder':
      return {
        label: t('erroraction.choose_folder'), iconName: 'folderOpen',
        run: async () => {
          if (await chooseFolder()) await retryJob(job, 'normal');
        },
      };
    case 'repair_engine':
      return {
        label: t('erroraction.repair_engine'), iconName: 'wrench',
        run: async () => {
          const res = await api.engine_repair(null);
          if (!res.ok) return showError(res.error);
          toast(t('engine.repairing_toast'), {
            kind: 'info',
            action: { label: t('engine.see_components'), fn: () => navigate('settings', { section: 'components' }) },
          });
        },
      };
    case 'open_browser':
      return { label: t('erroraction.open_browser'), iconName: 'external', run: () => openJobSource(job) };
    default:
      return null;
  }
}

// ---------------------------------------------------------------- URLs typed / pasted / dropped by the user
const URL_RE = /https?:\/\/[^\s<>"'`]+/gi;

/** All http(s) URLs in a text, trimmed of trailing punctuation. */
export function extractUrls(text) {
  if (!text) return [];
  const found = String(text).match(URL_RE) || [];
  const out = [];
  for (let raw of found) {
    raw = raw.replace(/[),.;:!?\]}>]+$/, '');
    try {
      const u = new URL(raw);
      if ((u.protocol === 'http:' || u.protocol === 'https:') && u.hostname.includes('.')) out.push(normalizeUrl(u));
    } catch { /* not a URL */ }
  }
  return [...new Set(out)];
}

/** Light normalization for display/dedupe; the backend still validates everything. */
export function normalizeUrl(u) {
  const url = u instanceof URL ? u : new URL(u);
  const host = url.hostname.toLowerCase();
  if (host === 'm.youtube.com' || host === 'music.youtube.com' || host === 'youtube.com') url.hostname = 'www.youtube.com';
  return url.toString();
}

/** Accepts bare domains typed by hand ("youtu.be/xyz"). */
export function coerceUrl(text) {
  const urls = extractUrls(text);
  if (urls.length) return urls;
  const trimmed = String(text || '').trim();
  if (/^[\w-]+(\.[\w-]+)+\/\S*$/.test(trimmed)) return extractUrls(`https://${trimmed}`);
  return [];
}

export function hasListParam(url) {
  try {
    const u = new URL(url);
    return u.searchParams.has('list') && !u.pathname.startsWith('/playlist');
  } catch {
    return false;
  }
}

export function isPlaylistPage(url) {
  try {
    const u = new URL(url);
    return u.pathname.startsWith('/playlist') && u.searchParams.has('list');
  } catch {
    return false;
  }
}

/** Video id for the filename preview when MediaView has no `id` (YouTube URLs only). */
export function guessVideoId(url) {
  try {
    const u = new URL(url);
    if (u.hostname === 'youtu.be') return u.pathname.slice(1).split('/')[0] || null;
    if (u.searchParams.get('v')) return u.searchParams.get('v');
    const m = /^\/(shorts|live|embed)\/([\w-]{6,})/.exec(u.pathname);
    return m ? m[2] : null;
  } catch {
    return null;
  }
}
