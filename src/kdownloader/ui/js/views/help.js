// S9 help: common problems (each opens open_help(code)), SmartScreen / Smart App Control, shortcuts, web links.
import { h, btn } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';
import { openHelp, openPage, navigate } from '../actions.js';

// Codes match engine/errors_catalog.json, so /ayuda#<code> on the web lands on the same entry.
const PROBLEMS = [
  { code: 'http_403', iconName: 'lock' },
  { code: 'engine_outdated', iconName: 'refresh' },
  { code: 'bot_check', iconName: 'shield' },
  { code: 'age_restricted', iconName: 'user' },
  { code: 'format_unavailable', iconName: 'layers' },
  { code: 'ffmpeg_missing', iconName: 'film' },
  { code: 'blocked_by_windows', iconName: 'monitor' },
  { code: 'permission', iconName: 'folder' },
  { code: 'disk_full', iconName: 'hardDrive' },
  { code: 'unsupported_url', iconName: 'link' },
];

const SHORTCUTS = [
  [['Ctrl', 'V'], 'help.kb_paste'],
  [['Enter'], 'help.kb_enter'],
  [['Esc'], 'help.kb_esc'],
  [['Ctrl', ','], 'help.kb_settings'],
  [['help.key_delete'], 'help.kb_delete'],
  [['Ctrl', 'L'], 'help.kb_focus'],
];

export function createHelp() {
  const problems = h('ul', { class: 'help-list' }, PROBLEMS.map((p, i) => h('li', { style: { '--i': String(Math.min(i, 8)) } },
    h('button', { class: 'help-item', type: 'button', on: { click: () => openHelp(p.code) } },
      h('span', { class: 'help-icon' }, icon(p.iconName, { size: 18 })),
      h('span', { class: 'help-text' },
        h('strong', { text: t(`help.problem.${p.code}.title`) }),
        h('span', { class: 'muted', text: t(`help.problem.${p.code}.text`) })),
      h('span', { class: 'help-go' }, icon('external', { size: 16 }))))));

  const kb = h('ul', { class: 'kb-list' }, SHORTCUTS.map(([keys, label]) => h('li', {},
    h('span', { class: 'kb-keys' }, keys.map((k, i) => [i ? '+' : null, h('kbd', { text: k.startsWith('help.') ? t(k) : k })])),
    h('span', { text: t(label) }))));

  const el = h('section', { class: 'view view-help', attrs: { 'aria-label': t('help.title') } },
    h('header', { class: 'page-head' },
      h('h1', { class: 'page-title', text: t('help.title') }),
      h('p', { class: 'page-lead muted', text: t('help.lead') })),
    h('div', { class: 'content stack-4' },
      h('section', { class: 'card help-card', attrs: { 'aria-labelledby': 'help-common' } },
        h('h2', { class: 'set-section-title', id: 'help-common' }, icon('help', { size: 18 }), h('span', { text: t('help.common') })),
        problems),
      h('section', { class: 'card help-card', attrs: { 'aria-labelledby': 'help-windows' } },
        h('h2', { class: 'set-section-title', id: 'help-windows' }, icon('shield', { size: 18 }), h('span', { text: t('help.windows_title') })),
        h('p', { text: t('help.windows_1') }),
        h('p', { text: t('help.windows_2') }),
        h('p', { class: 'muted small', text: t('help.windows_3') }),
        h('div', { class: 'set-actions' },
          btn({ label: t('help.components_btn'), iconName: 'wrench', kind: 'secondary', size: 'sm', onClick: () => navigate('settings', { section: 'components' }) }),
          btn({ label: t('help.windows_more'), iconName: 'external', kind: 'ghost', size: 'sm', onClick: () => openHelp('blocked_by_windows') }))),
      h('section', { class: 'card help-card', attrs: { 'aria-labelledby': 'help-kb' } },
        h('h2', { class: 'set-section-title', id: 'help-kb' }, icon('keyboard', { size: 18 }), h('span', { text: t('help.shortcuts') })),
        kb),
      h('section', { class: 'card help-card help-web' },
        h('div', {},
          h('strong', { text: t('help.web_title') }),
          h('p', { class: 'muted', text: t('help.web_text') })),
        h('div', { class: 'set-actions' },
          btn({ label: t('help.web_btn'), iconName: 'book', kind: 'primary', size: 'sm', onClick: () => openPage('help') }),
          btn({ label: t('about.link_issues'), iconName: 'bug', kind: 'ghost', size: 'sm', onClick: () => openPage('issues') })))));

  return { el, destroy() {}, show() {} };
}
