// Small DOM helpers. Everything dynamic goes through textContent / setAttribute: no innerHTML anywhere.
import { icon } from './icons.js';

/**
 * h('div', {class: 'x', text: 'hola', on: {click}, attrs: {...}, dataset: {...}}, ...children)
 * children: Node | string | number | null | false | arrays of those. Strings become text nodes.
 */
export function h(tag, props, ...children) {
  const el = document.createElement(tag);
  if (props) applyProps(el, props);
  append(el, children);
  return el;
}

export function applyProps(el, props) {
  for (const [key, value] of Object.entries(props)) {
    if (value === undefined || value === null || value === false) continue;
    switch (key) {
      case 'class':
        el.className = Array.isArray(value) ? value.filter(Boolean).join(' ') : value;
        break;
      case 'text':
        el.textContent = String(value);
        break;
      case 'on':
        for (const [evt, fn] of Object.entries(value)) el.addEventListener(evt, fn);
        break;
      case 'attrs':
        for (const [name, v] of Object.entries(value)) {
          if (v === undefined || v === null || v === false) continue;
          el.setAttribute(name, v === true ? '' : String(v));
        }
        break;
      case 'dataset':
        for (const [name, v] of Object.entries(value)) {
          if (v !== undefined && v !== null) el.dataset[name] = String(v);
        }
        break;
      case 'style':
        for (const [name, v] of Object.entries(value)) el.style.setProperty(name, String(v));
        break;
      case 'hidden':
        el.hidden = Boolean(value);
        break;
      default:
        // Known safe DOM properties only (value, checked, type, disabled, tabIndex, htmlFor, id, title...).
        if (key.startsWith('aria') || key === 'role') el.setAttribute(key === 'role' ? 'role' : toAria(key), String(value));
        else el[key] = value;
    }
  }
}

function toAria(key) {
  // ariaLabel -> aria-label
  return 'aria-' + key.slice(4).replace(/[A-Z]/g, (m) => '-' + m.toLowerCase()).replace(/^-/, '');
}

export function append(el, children) {
  for (const child of children.flat(Infinity)) {
    if (child === null || child === undefined || child === false || child === true) continue;
    el.appendChild(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

export function clear(el) {
  while (el.firstChild) el.removeChild(el.firstChild);
  return el;
}

export function setText(el, value) {
  const text = value === null || value === undefined ? '' : String(value);
  if (el.textContent !== text) el.textContent = text;
}

export function toggle(el, cls, on) {
  if (el.classList.contains(cls) !== Boolean(on)) el.classList.toggle(cls, Boolean(on));
}

/** Button helper: btn({label, icon, kind, onClick, title, size}) */
export function btn({ label, iconName, kind = 'secondary', onClick, title, size, attrs, cls, iconOnly = false, type = 'button' }) {
  const b = h('button', {
    class: ['btn', `btn-${kind}`, size ? `btn-${size}` : '', iconOnly ? 'btn-icon' : '', cls],
    type,
    attrs: { ...(attrs || {}), title: title || (iconOnly ? label : null), 'aria-label': iconOnly ? label : null },
    on: onClick ? { click: onClick } : null,
  });
  if (iconName) b.appendChild(icon(iconName));
  if (!iconOnly && label) b.appendChild(h('span', { class: 'btn-label', text: label }));
  return b;
}

/** Image that hides itself if it fails (thumbnails are remote https or data:). */
export function thumbImg(src, alt = '') {
  const img = h('img', { attrs: { alt, loading: 'lazy', decoding: 'async', draggable: 'false', referrerpolicy: 'no-referrer' } });
  if (src && /^(https:|data:image\/)/.test(src)) {
    img.addEventListener('error', () => img.classList.add('img-failed'), { once: true });
    img.src = src;
  } else {
    img.classList.add('img-failed');
  }
  return img;
}

export function isEditable(target) {
  if (!target || !(target instanceof Element)) return false;
  if (target.isContentEditable) return true;
  const tag = target.tagName;
  if (tag === 'TEXTAREA') return true;
  if (tag === 'INPUT') {
    const type = (target.getAttribute('type') || 'text').toLowerCase();
    return !['checkbox', 'radio', 'button', 'submit', 'range', 'color', 'file'].includes(type);
  }
  return false;
}

export function prefersReducedMotion() {
  return document.documentElement.dataset.motion === 'reduce' ||
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function debounce(fn, ms) {
  let timer = 0;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
