// S7 history: search, groups (Hoy / Ayer / Esta semana / Antes), open / show / redownload / copy link / remove / clear.
import { h, btn, clear, setText, thumbImg, debounce } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';
import { store } from '../store.js';
import { api } from '../api.js';
import { formatBytes, formatTime, formatDate, optionName, toMs } from '../format.js';
import { menuButton, confirmDialog } from '../ui/feedback.js';
import { showError, copyText, navigate } from '../actions.js';

function groupOf(ts) {
  const ms = toMs(ts);
  if (ms === null) return 'older';
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const startDay = today.getTime();
  if (ms >= startDay) return 'today';
  if (ms >= startDay - 86400000) return 'yesterday';
  // "Esta semana": the last 7 days.
  if (ms >= startDay - 6 * 86400000) return 'week';
  return 'older';
}

export function createHistory({ onRedownload }) {
  const unsubs = [];
  let items = [];
  let reqSeq = 0;

  const search = h('input', {
    class: 'search-input', type: 'search', placeholder: t('history.search'), value: store.ui.historyQuery || '',
    attrs: { 'aria-label': t('history.search'), autocomplete: 'off', spellcheck: 'false' },
  });
  const clearAll = btn({ label: t('history.clear'), iconName: 'trash', kind: 'ghost', size: 'sm', onClick: async () => {
    const yes = await confirmDialog({ title: t('history.clear_title'), message: t('history.clear_body'), confirmLabel: t('history.clear_yes'), danger: true });
    if (!yes) return;
    const res = await api.history_clear();
    if (!res.ok) return showError(res.error);
    load();
  } });
  const listEl = h('div', { class: 'history-groups' });
  const count = h('span', { class: 'muted num' });
  const header = h('header', { class: 'page-head sticky-head' },
    h('div', { class: 'page-head-row' }, h('h1', { class: 'page-title', text: t('history.title') }), count, h('span', { class: 'spacer' }), clearAll),
    h('div', { class: 'search' }, icon('search', { size: 16 }), search));
  const el = h('section', { class: 'view view-history', attrs: { 'aria-label': t('history.title') } }, header, h('div', { class: 'content' }, listEl));

  search.addEventListener('input', debounce(() => {
    store.ui.historyQuery = search.value;
    load();
  }, 200));
  search.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && search.value) {
      e.stopPropagation();
      search.value = '';
      store.ui.historyQuery = '';
      load();
    }
  });

  async function load() {
    const seq = ++reqSeq;
    const res = await api.history(store.ui.historyQuery || '');
    if (seq !== reqSeq) return;
    if (!res.ok) {
      showError(res.error);
      return;
    }
    items = Array.isArray(res.items) ? res.items : [];
    render();
  }

  function itemRow(item) {
    const gone = item.file_exists === false;
    const metaParts = [item.uploader, optionName(item.option), formatBytes(item.size), groupOf(item.finished_at) === 'today' || groupOf(item.finished_at) === 'yesterday' ? formatTime(item.finished_at) : formatDate(item.finished_at)].filter(Boolean);
    const open = btn({ label: t('jobs.action.open'), iconName: 'play', kind: 'soft', size: 'sm', onClick: async () => {
      const r = await api.open_file(item.id);
      if (!r.ok) showError(r.error, 'jobs.open_failed');
    } });
    open.disabled = gone;
    const folder = btn({ label: t('jobs.action.show_folder'), iconName: 'folderOpen', kind: 'ghost', iconOnly: true, onClick: async () => {
      const r = await api.show_in_folder(item.id);
      if (!r.ok) showError(r.error, 'jobs.open_failed');
    } });
    folder.disabled = gone;
    const menu = menuButton(t('jobs.action.more'), () => [
      item.url ? { label: t('history.redownload'), iconName: 'download', onSelect: () => onRedownload(item.url) } : null,
      item.url ? { label: t('history.copy_link'), iconName: 'link', onSelect: () => copyText(item.url, 'history.link_copied') } : null,
      { label: t('history.remove'), iconName: 'trash', danger: true, onSelect: async () => {
        const r = await api.history_remove(item.id);
        if (!r.ok) return showError(r.error);
        items = items.filter((x) => x.id !== item.id);
        render();
      } },
    ]);
    return h('li', { class: ['hist-item', gone ? 'gone' : ''], dataset: { id: item.id } },
      h('div', { class: 'hist-thumb' }, thumbImg(item.thumbnail), h('span', { class: 'job-thumb-fallback' }, icon(item.container === 'mp3' || item.container === 'm4a' ? 'music' : 'film', { size: 18 }))),
      h('div', { class: 'hist-body' },
        h('div', { class: 'hist-title', text: item.title || item.file_name || '', attrs: { title: item.title || '' } }),
        h('div', { class: 'hist-meta muted' }, h('span', { class: 'num', text: metaParts.join(' · ') }),
          gone ? h('span', { class: ['chip', 'chip-note', 'note-gone'] }, icon('alert', { size: 13 }), h('span', { text: t('jobs.note.file_missing') })) : null)),
      h('div', { class: 'hist-actions' }, open, folder, menu));
  }

  function render() {
    clear(listEl);
    setText(count, items.length ? t('history.count', { count: items.length }) : '');
    clearAll.hidden = !items.length || Boolean(store.ui.historyQuery);
    if (!items.length) {
      const q = store.ui.historyQuery;
      listEl.append(h('div', { class: 'empty empty-sm' },
        h('div', { class: 'empty-art', attrs: { 'aria-hidden': 'true' } }, h('span', { class: 'empty-orb' }), icon(q ? 'search' : 'history', { size: 30, strokeWidth: 1.8 })),
        h('h2', { class: 'empty-title', text: q ? t('history.no_results', { q }) : t('history.empty_title') }),
        h('p', { class: 'empty-text', text: q ? t('history.no_results_hint') : t('history.empty_text') }),
        q ? null : btn({ label: t('history.go_download'), iconName: 'download', kind: 'primary', onClick: () => navigate('home') })));
      return;
    }
    const groups = { today: [], yesterday: [], week: [], older: [] };
    for (const it of [...items].sort((a, b) => (b.finished_at || 0) - (a.finished_at || 0))) groups[groupOf(it.finished_at)].push(it);
    let i = 0;
    for (const [key, list] of Object.entries(groups)) {
      if (!list.length) continue;
      const ul = h('ul', { class: 'hist-list' });
      for (const it of list) {
        const row = itemRow(it);
        row.style.setProperty('--i', String(Math.min(i++, 8)));
        ul.append(row);
      }
      listEl.append(h('section', { class: 'hist-group', attrs: { 'aria-label': t(`history.group.${key}`) } },
        h('h2', { class: 'group-title', text: t(`history.group.${key}`) }), ul));
    }
  }

  // New finished jobs make the list stale.
  unsubs.push(store.on('job', (job, prev) => {
    if (job.state === 'done' && (!prev || prev.state !== 'done')) {
      if (store.route === 'history') load();
    }
  }));

  return {
    el,
    destroy() {
      unsubs.forEach((u) => u());
    },
    show() {
      load();
    },
    focusSearch() {
      search.focus();
    },
  };
}
