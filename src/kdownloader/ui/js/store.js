// Tiny store: AppState from Python + UI-only state, with topic subscriptions.
// Events from Python (window.kd.emit) land in applyEvent(); views subscribe to topics and patch themselves.

const topics = new Map();

export const store = {
  /** AppState without `jobs` (jobs live in the map below, keyed by id). */
  state: null,
  jobs: new Map(),
  route: 'home',
  lang: 'es',
  systemLang: null,
  /** UI state that must survive view re-creation (language switch). */
  ui: {
    home: {
      input: '',
      stage: 'idle', // idle | probing | media | error
      url: null,
      media: null,
      singleMedia: null,
      listMedia: null,
      scope: 'one', // one | all
      error: null,
      selected: null,
      moreOpen: false,
      remember: false,
      seq: 0,
      probeStarted: 0,
    },
    filter: 'all',
    settingsSection: 'general',
    historyQuery: '',
    dismissedUpdate: null,
    dismissedNotice: null,
    clipboardSuggested: null,
  },
  mode: 'pywebview', // pywebview | mock

  on(topic, fn) {
    if (!topics.has(topic)) topics.set(topic, new Set());
    topics.get(topic).add(fn);
    return () => topics.get(topic)?.delete(fn);
  },
  emit(topic, ...args) {
    const set = topics.get(topic);
    if (!set) return;
    for (const fn of [...set]) {
      try {
        fn(...args);
      } catch (err) {
        console.error(`[store] listener de "${topic}" falló`, err);
      }
    }
  },
  get settings() {
    return this.state ? this.state.settings : null;
  },
  get engine() {
    return this.state ? this.state.engine : null;
  },
};

const pending = [];

function navigatorLang() {
  const nav = (navigator.language || 'es').toLowerCase();
  return nav.startsWith('es') ? 'es' : 'en';
}

function resolveLang() {
  const pref = store.state?.settings?.language;
  if (pref === 'es' || pref === 'en') return pref;
  return store.systemLang || navigatorLang();
}

function refreshLang() {
  const next = resolveLang();
  if (next !== store.lang) {
    store.lang = next;
    store.emit('lang', next);
  }
}

export function setState(state) {
  if (!state || typeof state !== 'object') return;
  const { jobs = [], ...rest } = state;
  const prevSettings = store.state?.settings;
  store.state = rest;
  if (rest.settings?.language === 'auto' && (rest.lang === 'es' || rest.lang === 'en')) store.systemLang = rest.lang;
  if (!store.systemLang) store.systemLang = rest.lang === 'en' || rest.lang === 'es' ? rest.lang : navigatorLang();

  const incoming = new Set();
  for (const job of jobs) {
    if (!job || !job.id) continue;
    incoming.add(job.id);
    upsertJob(job);
  }
  for (const id of [...store.jobs.keys()]) {
    if (!incoming.has(id)) removeJob(id);
  }
  refreshLang();
  store.emit('state', store.state);
  if (JSON.stringify(prevSettings) !== JSON.stringify(rest.settings)) store.emit('settings', rest.settings);
  store.emit('engine', rest.engine);
  store.emit('update', rest.update);
  store.emit('notice', rest.notice);
  while (pending.length) applyEvent(pending.shift());
}

export function setSettings(settings) {
  if (!settings || !store.state) return;
  store.state.settings = settings;
  refreshLang();
  store.emit('settings', settings);
}

export function setEngine(engine) {
  if (!engine || !store.state) return;
  store.state.engine = engine;
  store.emit('engine', engine);
}

function upsertJob(job) {
  const prev = store.jobs.get(job.id) || null;
  store.jobs.set(job.id, job);
  store.emit('job', job, prev);
}

function removeJob(id) {
  if (!store.jobs.has(id)) return;
  store.jobs.delete(id);
  store.emit('job_removed', id);
}

/** Entry point for every Python -> JS event (see docs/architecture.md §5). */
export function applyEvent(evt) {
  if (!evt || typeof evt !== 'object' || typeof evt.type !== 'string') return;
  if (!store.state && evt.type !== 'state' && evt.type !== 'job' && evt.type !== 'job_removed') {
    pending.push(evt);
    return;
  }
  switch (evt.type) {
    case 'state':
      setState(evt.state);
      break;
    case 'job':
      if (evt.job && evt.job.id) upsertJob(evt.job);
      break;
    case 'job_removed':
      removeJob(evt.id);
      break;
    case 'engine':
      setEngine(evt.engine);
      break;
    case 'settings':
      setSettings(evt.settings);
      break;
    case 'incoming_url':
      if (typeof evt.url === 'string') store.emit('incoming_url', evt.url);
      break;
    case 'update':
      store.state.update = evt.update || null;
      store.emit('update', store.state.update);
      break;
    case 'notice':
      store.state.notice = evt.notice || null;
      store.emit('notice', store.state.notice);
      break;
    case 'confirm_close':
      store.emit('confirm_close', Number(evt.active) || 0);
      break;
    default:
      console.debug('[store] evento desconocido', evt.type);
  }
}

export function jobsSorted() {
  return [...store.jobs.values()].sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
}

export const ACTIVE_STATES = new Set(['queued', 'probing', 'downloading', 'processing']);
export const FAILED_STATES = new Set(['error', 'interrupted']);

export function isActive(job) {
  return ACTIVE_STATES.has(job.state);
}
