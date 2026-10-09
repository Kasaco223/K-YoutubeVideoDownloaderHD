// Toasts, aria-live announcements, modals (native <dialog> + focus trap) and popover menus.
import { h, btn, clear } from '../dom.js';
import { icon } from '../icons.js';
import { t } from '../i18n.js';

// ---------------------------------------------------------------- live region (milestones only)
let liveTimer = 0;
export function announce(message) {
  const live = document.getElementById('live');
  if (!live) return;
  live.textContent = '';
  clearTimeout(liveTimer);
  liveTimer = setTimeout(() => {
    live.textContent = message;
  }, 60);
}

// ---------------------------------------------------------------- toasts
const TOAST_ICONS = { info: 'info', success: 'checkCircle', error: 'alertCircle', warning: 'alert' };

export function toast(message, { kind = 'info', action = null, timeout = 4200 } = {}) {
  const host = document.getElementById('toasts');
  if (!host) return () => {};
  const el = h('div', { class: ['toast', `toast-${kind}`], role: kind === 'error' ? 'alert' : 'status' },
    h('span', { class: 'toast-icon' }, icon(TOAST_ICONS[kind] || 'info')),
    h('span', { class: 'toast-text', text: message }));
  let closed = false;
  const close = () => {
    if (closed) return;
    closed = true;
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 220);
  };
  if (action) {
    el.appendChild(btn({ label: action.label, kind: 'ghost', size: 'sm', onClick: () => { close(); action.fn(); } }));
  }
  el.appendChild(btn({ label: t('common.close'), iconName: 'x', kind: 'ghost', size: 'sm', iconOnly: true, onClick: close, cls: 'toast-close' }));
  host.appendChild(el);
  while (host.children.length > 3) host.firstElementChild.remove();
  if (timeout) setTimeout(close, timeout);
  return close;
}

// ---------------------------------------------------------------- modals
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * openModal({title, body: Node|string, actions: [{label, kind, value, iconName}], icon, tone, dismissValue})
 * Resolves with the chosen action's value (dismissValue on Esc / close).
 */
export function openModal({ title, body, actions = [], iconName = null, tone = 'default', dismissValue = null, labelledBy = null }) {
  return new Promise((resolve) => {
    const opener = document.activeElement;
    const titleId = labelledBy || `dlg-${Math.random().toString(36).slice(2, 8)}`;
    const dialog = h('dialog', { class: ['modal', `modal-${tone}`], attrs: { 'aria-labelledby': titleId } });
    const head = h('div', { class: 'modal-head' },
      iconName ? h('span', { class: 'modal-icon' }, icon(iconName, { size: 22 })) : null,
      h('h2', { class: 'modal-title', id: titleId, text: title }));
    const content = h('div', { class: 'modal-body' }, typeof body === 'string' ? h('p', { text: body }) : body);
    const footer = h('div', { class: 'modal-actions' });
    let done = false;
    const finish = (value) => {
      if (done) return;
      done = true;
      dialog.classList.add('closing');
      setTimeout(() => {
        try { dialog.close(); } catch { /* already closed */ }
        dialog.remove();
        if (opener && typeof opener.focus === 'function' && document.contains(opener)) opener.focus();
      }, 160);
      resolve(value);
    };
    for (const a of actions) {
      footer.appendChild(btn({ label: a.label, kind: a.kind || 'secondary', iconName: a.iconName, onClick: () => finish(a.value) }));
    }
    dialog.append(head, content, footer);
    dialog.addEventListener('cancel', (e) => {
      e.preventDefault();
      finish(dismissValue);
    });
    dialog.addEventListener('click', (e) => {
      if (e.target === dialog) finish(dismissValue); // click on the backdrop
    });
    dialog.addEventListener('keydown', (e) => {
      if (e.key !== 'Tab') return;
      const items = [...dialog.querySelectorAll(FOCUSABLE)].filter((n) => n.offsetParent !== null);
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    });
    document.body.appendChild(dialog);
    dialog.showModal();
    // Default focus: the primary action, else the safe (non-destructive) one. Never a danger button.
    const primary = footer.querySelector('.btn-primary') || footer.querySelector('.btn:not(.btn-danger)') || footer.querySelector('button');
    (primary || dialog).focus();
  });
}

export function confirmDialog({ title, message, confirmLabel, cancelLabel, danger = false, iconName = null }) {
  return openModal({
    title,
    body: message,
    iconName: iconName || (danger ? 'alert' : null),
    tone: danger ? 'danger' : 'default',
    dismissValue: false,
    actions: [
      { label: cancelLabel || t('common.cancel'), kind: 'secondary', value: false },
      { label: confirmLabel || t('common.ok'), kind: danger ? 'danger' : 'primary', value: true },
    ],
  });
}

export function isModalOpen() {
  return Boolean(document.querySelector('dialog.modal[open]'));
}

// ---------------------------------------------------------------- popover menu
let openMenuState = null;

export function closeMenu() {
  if (!openMenuState) return false;
  const { el, anchor, onDoc } = openMenuState;
  openMenuState = null;
  el.remove();
  anchor.setAttribute('aria-expanded', 'false');
  document.removeEventListener('pointerdown', onDoc, true);
  return true;
}

/** items: [{label, iconName, onSelect, danger, disabled}] */
export function openMenu(anchor, items) {
  if (openMenuState && openMenuState.anchor === anchor) {
    closeMenu();
    return;
  }
  closeMenu();
  const el = h('div', { class: 'menu', role: 'menu' });
  for (const item of items) {
    if (!item) continue;
    const mi = h('button', {
      class: ['menu-item', item.danger ? 'danger' : ''], type: 'button', role: 'menuitem', disabled: Boolean(item.disabled), tabIndex: -1,
      on: { click: () => { closeMenu(); item.onSelect(); } },
    }, item.iconName ? icon(item.iconName, { size: 16 }) : null, h('span', { text: item.label }));
    el.appendChild(mi);
  }
  el.addEventListener('keydown', (e) => {
    const list = [...el.querySelectorAll('.menu-item:not([disabled])')];
    const idx = list.indexOf(document.activeElement);
    if (e.key === 'ArrowDown') { e.preventDefault(); list[(idx + 1) % list.length]?.focus(); }
    if (e.key === 'ArrowUp') { e.preventDefault(); list[(idx - 1 + list.length) % list.length]?.focus(); }
    if (e.key === 'Home') { e.preventDefault(); list[0]?.focus(); }
    if (e.key === 'End') { e.preventDefault(); list[list.length - 1]?.focus(); }
    if (e.key === 'Escape' || e.key === 'Tab') { e.preventDefault(); e.stopPropagation(); closeMenu(); anchor.focus(); }
  });
  document.body.appendChild(el);
  const r = anchor.getBoundingClientRect();
  const mw = el.offsetWidth;
  const mh = el.offsetHeight;
  let left = Math.min(window.innerWidth - mw - 8, Math.max(8, r.right - mw));
  let top = r.bottom + 6;
  if (top + mh > window.innerHeight - 8) top = Math.max(8, r.top - mh - 6);
  el.style.left = `${left}px`;
  el.style.top = `${top}px`;
  anchor.setAttribute('aria-expanded', 'true');
  const onDoc = (e) => {
    if (!el.contains(e.target) && e.target !== anchor && !anchor.contains(e.target)) closeMenu();
  };
  document.addEventListener('pointerdown', onDoc, true);
  openMenuState = { el, anchor, onDoc };
  el.querySelector('.menu-item:not([disabled])')?.focus();
}

export function menuButton(label, getItems) {
  const b = btn({ label, iconName: 'more', kind: 'ghost', iconOnly: true, attrs: { 'aria-haspopup': 'menu', 'aria-expanded': 'false' } });
  b.addEventListener('click', (e) => {
    e.stopPropagation();
    openMenu(b, getItems());
  });
  return b;
}

export { clear };
