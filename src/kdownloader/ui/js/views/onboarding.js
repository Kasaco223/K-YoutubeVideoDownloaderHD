// S0 welcome: responsible use -> engine setup -> folder + favorite format -> "¡Listo!" -> finish_onboarding.
import { h, btn, clear, setText, prefersReducedMotion } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';
import { store, setSettings } from '../store.js';
import { api } from '../api.js';
import { formatPercent } from '../format.js';
import { chooseFolder, saveSettings, showError } from '../actions.js';
import { createComponentRows, engineProgress } from './components.js';
import { burst } from '../ui/confetti.js';

const STEPS = ['terms', 'setup', 'prefs', 'ready'];
const FAVS = [
  { key: 'recommended', iconName: 'sparkles' },
  { key: 'max', iconName: 'zap' },
  { key: 'mp3', iconName: 'music' },
];

export function createOnboarding({ onFinish }) {
  const ui = store.ui;
  if (!ui.onbStep) ui.onbStep = store.settings?.accepted_terms ? 'setup' : 'terms';
  if (!ui.onbFavorite) ui.onbFavorite = ['recommended', 'max', 'mp3'].includes(store.settings?.favorite_preset) ? store.settings.favorite_preset : 'recommended';
  const unsubs = [];

  const stage = h('div', { class: 'onb-stage' });
  const dots = h('ol', { class: 'onb-dots', attrs: { 'aria-label': t('onb.progress_label') } });
  const el = h('section', { class: 'view view-onb', attrs: { 'aria-label': t('onb.label') } },
    h('div', { class: 'aurora onb-aurora', attrs: { 'aria-hidden': 'true' } }),
    h('div', { class: 'onb-wrap' }, stage, dots));

  function renderDots() {
    clear(dots);
    const idx = STEPS.indexOf(ui.onbStep);
    STEPS.forEach((s, i) => dots.append(h('li', {
      class: ['onb-dot', i < idx ? 'done' : '', i === idx ? 'current' : ''],
      attrs: { 'aria-current': i === idx ? 'step' : null, 'aria-label': t('onb.step_n', { i: i + 1, n: STEPS.length }) },
    })));
  }

  function go(step) {
    ui.onbStep = step;
    render();
    requestAnimationFrame(() => stage.querySelector('h1')?.focus());
  }

  function langSwitch() {
    const seg = h('div', { class: 'segmented segmented-sm', role: 'radiogroup', attrs: { 'aria-label': t('settings.language') } });
    for (const [value, label] of [['es', 'Español'], ['en', 'English']]) {
      seg.append(h('button', {
        class: 'seg', type: 'button', role: 'radio', attrs: { 'aria-checked': String(store.lang === value), lang: value },
        on: { click: () => saveSettings({ language: value }) },
      }, h('span', { text: label })));
    }
    return h('div', { class: 'onb-lang' }, icon('globe', { size: 16 }), seg);
  }

  // ---------------------------------------------------------------- step 1: responsible use
  function termsStep() {
    const check = h('input', { type: 'checkbox', id: 'onb-terms', checked: Boolean(ui.onbAccepted) });
    const next = btn({ label: t('common.continue'), iconName: 'arrowRight', kind: 'cta', size: 'lg', cls: 'icon-end' });
    next.disabled = !check.checked;
    check.addEventListener('change', () => {
      ui.onbAccepted = check.checked;
      next.disabled = !check.checked;
    });
    next.addEventListener('click', async () => {
      next.disabled = true;
      const res = await api.accept_terms();
      if (!res.ok) {
        next.disabled = false;
        return showError(res.error);
      }
      if (res.settings) setSettings(res.settings);
      go('setup');
    });
    return h('div', { class: 'onb-card enter' },
      h('img', { class: 'onb-logo', src: 'assets/logo.svg', alt: '', width: 72, height: 72, attrs: { draggable: 'false' } }),
      h('h1', { class: 'onb-title', tabIndex: -1, text: t('onb.welcome_title') }),
      h('p', { class: 'onb-lead', text: t('onb.welcome_lead') }),
      h('div', { class: 'responsible-card' },
        h('div', { class: 'responsible-head' }, icon('shield', { size: 20 }), h('strong', { text: t('onb.responsible_title') })),
        h('ul', { class: 'responsible-list' },
          ['onb.responsible_1', 'onb.responsible_2', 'onb.responsible_3'].map((k) => h('li', { text: t(k) }))),
        h('p', { class: 'muted small', text: t('about.not_affiliated') })),
      h('label', { class: 'check check-lg', htmlFor: 'onb-terms' }, check,
        h('span', { class: 'check-box' }, icon('check', { size: 12, strokeWidth: 3 })),
        h('span', { text: t('onb.understand') })),
      h('div', { class: 'onb-foot' }, langSwitch(), next));
  }

  // ---------------------------------------------------------------- step 2: engine setup
  let rows = null;
  let totalBar = null;
  let totalText = null;
  let setupNext = null;
  function setupStep() {
    rows = createComponentRows('onboarding');
    const fill = h('div', { class: 'bar-fill' });
    totalBar = h('div', { class: 'bar bar-lg', role: 'progressbar', attrs: { 'aria-valuemin': '0', 'aria-valuemax': '100', 'aria-label': t('onb.setup_title') } }, fill);
    totalBar._fill = fill;
    totalText = h('span', { class: 'num muted' });
    setupNext = btn({ label: t('common.continue'), iconName: 'arrowRight', kind: 'cta', size: 'lg', cls: 'icon-end', onClick: () => go('prefs') });
    const card = h('div', { class: 'onb-card enter' },
      h('div', { class: 'onb-icon' }, icon('package', { size: 28 })),
      h('h1', { class: 'onb-title', tabIndex: -1, text: t('onb.setup_title') }),
      h('p', { class: 'onb-lead', text: t('onb.setup_lead') }),
      rows.el,
      h('div', { class: 'onb-total' }, totalBar, totalText),
      h('p', { class: 'muted small', text: t('onb.setup_note') }),
      h('div', { class: 'onb-foot' }, btn({ label: t('common.back'), iconName: 'arrowLeft', kind: 'ghost', onClick: () => go('terms') }), setupNext));
    syncSetup();
    if (!ui.onbSetupStarted && !(store.engine && store.engine.ready)) {
      ui.onbSetupStarted = true;
      api.engine_setup().then((res) => { if (!res.ok) showError(res.error); });
    }
    return card;
  }

  function syncSetup() {
    if (!rows || !store.engine) return;
    rows.update(store.engine);
    const p = engineProgress(store.engine);
    const ready = Boolean(store.engine.ready);
    totalBar._fill.style.width = `${Math.round((ready ? 1 : p || 0) * 100)}%`;
    totalBar.setAttribute('aria-valuenow', String(Math.round((ready ? 1 : p || 0) * 100)));
    totalBar.classList.toggle('complete', ready);
    setText(totalText, ready ? t('onb.setup_ready') : t('onb.setup_progress', { pct: formatPercent(p || 0) }));
    setupNext.disabled = !ready;
    setText(setupNext.querySelector('.btn-label'), ready ? t('common.continue') : t('onb.setup_wait'));
  }

  // ---------------------------------------------------------------- step 3: folder + favorite
  function prefsStep() {
    const path = h('span', { class: 'dest-path', text: store.settings?.download_dir || '', attrs: { title: store.settings?.download_dir || '' } });
    const tiles = h('div', { class: 'options options-onb', role: 'radiogroup', attrs: { 'aria-label': t('onb.format_title') } });
    const radios = [];
    const select = (key, focus) => {
      ui.onbFavorite = key;
      for (const r of radios) {
        const on = r.dataset.key === key;
        r.setAttribute('aria-checked', String(on));
        r.tabIndex = on ? 0 : -1;
        if (on && focus) r.focus();
      }
    };
    FAVS.forEach((f, i) => {
      const tile = h('button', {
        class: ['tile', `tile-${f.key}`], type: 'button', role: 'radio', dataset: { key: f.key }, attrs: { 'aria-checked': 'false' }, tabIndex: -1,
        on: {
          click: () => select(f.key),
          keydown: (e) => {
            const d = e.key === 'ArrowRight' || e.key === 'ArrowDown' ? 1 : e.key === 'ArrowLeft' || e.key === 'ArrowUp' ? -1 : 0;
            if (!d) return;
            e.preventDefault();
            select(FAVS[(i + d + FAVS.length) % FAVS.length].key, true);
          },
        },
      },
      h('span', { class: 'tile-top' }, h('span', { class: 'tile-icon' }, icon(f.iconName, { size: 18 })), h('span', { class: 'tile-check' }, icon('check', { size: 12, strokeWidth: 3 }))),
      h('span', { class: 'tile-name', text: t(`option.${f.key}.name`) }),
      h('span', { class: 'tile-label', text: t(`option.${f.key}.summary`) }),
      h('span', { class: 'tile-hint', text: t(`option.${f.key}.hint`) }));
      radios.push(tile);
      tiles.append(tile);
    });
    select(ui.onbFavorite);
    const card = h('div', { class: 'onb-card onb-card-wide enter' },
      h('div', { class: 'onb-icon' }, icon('folderOpen', { size: 28 })),
      h('h1', { class: 'onb-title', tabIndex: -1, text: t('onb.prefs_title') }),
      h('p', { class: 'onb-lead', text: t('onb.prefs_lead') }),
      h('div', { class: 'dest dest-onb' },
        h('span', { class: 'dest-pill' }, icon('folder', { size: 16 }), path),
        btn({ label: t('common.change'), iconName: 'folderOpen', kind: 'secondary', size: 'sm', onClick: () => chooseFolder() })),
      h('h2', { class: 'onb-subtitle', text: t('onb.format_title') }),
      tiles,
      h('p', { class: 'muted small', text: t('onb.prefs_note') }),
      h('div', { class: 'onb-foot' },
        btn({ label: t('common.back'), iconName: 'arrowLeft', kind: 'ghost', onClick: () => go('setup') }),
        btn({ label: t('common.next'), iconName: 'arrowRight', kind: 'cta', size: 'lg', cls: 'icon-end', onClick: () => go('ready') })));
    card._path = path;
    return card;
  }

  // ---------------------------------------------------------------- step 4: ready
  function readyStep() {
    const start = btn({ label: t('onb.start'), iconName: 'download', kind: 'cta', size: 'lg' });
    start.addEventListener('click', async () => {
      start.disabled = true;
      const res = await api.finish_onboarding({ favorite_preset: ui.onbFavorite });
      if (!res.ok) {
        start.disabled = false;
        return showError(res.error);
      }
      if (res.settings) setSettings(res.settings);
      if (store.state) store.state.first_run = false;
      ui.onbStep = null;
      onFinish();
    });
    const card = h('div', { class: 'onb-card enter onb-ready' },
      h('div', { class: 'ready-mark' }, icon('check', { size: 40, strokeWidth: 2.6 })),
      h('h1', { class: 'onb-title', tabIndex: -1, text: t('onb.ready_title') }),
      h('p', { class: 'onb-lead', text: t('onb.ready_lead') }),
      h('div', { class: 'empty-tips' },
        h('span', { class: 'tip' }, h('kbd', { text: 'Ctrl' }), '+', h('kbd', { text: 'V' }), h('span', { text: t('home.tip_paste') })),
        h('span', { class: 'tip' }, icon('dropDown', { size: 15 }), h('span', { text: t('home.tip_drop') }))),
      h('div', { class: 'onb-foot onb-foot-center' }, start));
    setTimeout(() => {
      if (prefersReducedMotion() || !card.isConnected) return;
      const mark = card.querySelector('.ready-mark');
      const r = mark.getBoundingClientRect();
      burst(r.left + r.width / 2, r.top + r.height / 2, 36);
    }, 420);
    return card;
  }

  function render() {
    clear(stage);
    const step = ui.onbStep;
    rows = null;
    if (step === 'terms') stage.append(termsStep());
    else if (step === 'setup') stage.append(setupStep());
    else if (step === 'prefs') stage.append(prefsStep());
    else stage.append(readyStep());
    renderDots();
  }

  unsubs.push(store.on('engine', () => syncSetup()));
  unsubs.push(store.on('settings', (s) => {
    const card = stage.querySelector('.onb-card');
    if (card && card._path) {
      setText(card._path, s.download_dir || '');
      card._path.title = s.download_dir || '';
    }
  }));

  render();

  return {
    el,
    destroy() {
      unsubs.forEach((u) => u());
    },
    show() {
      stage.querySelector('h1')?.focus();
    },
  };
}
