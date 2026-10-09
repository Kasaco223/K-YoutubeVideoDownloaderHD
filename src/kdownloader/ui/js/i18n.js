// i18n: every visible string comes from i18n/<lang>.json. t('a.b.c', {var}) with {var} placeholders.
// Plurals: when vars.count is a number, "<key>_one" / "<key>_other" are tried first.

const dicts = { es: {}, en: {} };
let current = 'es';

export const LANGS = ['es', 'en'];

export async function loadDictionaries() {
  await Promise.all(LANGS.map(async (lang) => {
    try {
      const res = await fetch(`i18n/${lang}.json`, { cache: 'no-cache' });
      if (res.ok) dicts[lang] = await res.json();
    } catch (err) {
      console.error('[i18n] no se pudo cargar', lang, err);
    }
  }));
}

export function setLang(lang) {
  current = LANGS.includes(lang) ? lang : 'es';
  document.documentElement.lang = current === 'es' ? 'es-419' : 'en';
  return current;
}

export function getLang() {
  return current;
}

function lookup(dict, key) {
  let node = dict;
  for (const part of key.split('.')) {
    if (node && typeof node === 'object' && part in node) node = node[part];
    else return undefined;
  }
  return typeof node === 'string' ? node : undefined;
}

function resolve(key, vars) {
  const order = [dicts[current], dicts.es, dicts.en];
  if (vars && typeof vars.count === 'number') {
    const suffix = vars.count === 1 ? '_one' : '_other';
    for (const d of order) {
      const s = lookup(d, key + suffix);
      if (s !== undefined) return s;
    }
  }
  for (const d of order) {
    const s = lookup(d, key);
    if (s !== undefined) return s;
  }
  return undefined;
}

export function t(key, vars) {
  const template = resolve(key, vars);
  if (template === undefined) {
    if (location.search.includes('mock=1')) console.warn('[i18n] falta la clave', key);
    return key;
  }
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (m, name) => (name in vars && vars[name] !== null && vars[name] !== undefined ? String(vars[name]) : m));
}

/** True when the key exists (used for optional strings like per-code help). */
export function has(key) {
  return resolve(key) !== undefined;
}

export function locale() {
  // "es" (comma decimals: 1,2 GB) is the neutral choice for most of Latin America.
  return current === 'es' ? 'es' : 'en-US';
}
