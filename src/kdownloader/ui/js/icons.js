/*
 * Inline SVG icons built from static shape lists (never from remote data).
 *
 * Icon shapes are derived from Lucide (https://lucide.dev).
 * Lucide is licensed under the ISC License:
 *   Copyright (c) for portions of Lucide are held by Cole Bemis 2013-2022 as part of Feather (MIT).
 *   All other copyright (c) for Lucide are held by Lucide Contributors 2022.
 *   Permission to use, copy, modify, and/or distribute this software for any purpose with or without
 *   fee is hereby granted, provided that the above copyright notice and this permission notice appear
 *   in all copies. THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES.
 */

const SVG_NS = 'http://www.w3.org/2000/svg';

const P = (d) => ['path', { d }];
const C = (cx, cy, r) => ['circle', { cx, cy, r }];
const R = (x, y, width, height, rx) => ['rect', { x, y, width, height, rx }];
const L = (x1, y1, x2, y2) => ['line', { x1, y1, x2, y2 }];

const ICONS = {
  download: [P('M12 15V3'), P('M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4'), P('m7 10 5 5 5-5')],
  history: [P('M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'), P('M3 3v5h5'), P('M12 7v5l4 2')],
  settings: [
    P('M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z'),
    C(12, 12, 3),
  ],
  help: [C(12, 12, 10), P('M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3'), P('M12 17h.01')],
  clipboard: [R(8, 2, 8, 4, 1), P('M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2')],
  paste: [P('M15 2H9a1 1 0 0 0-1 1v2c0 .6.4 1 1 1h6c.6 0 1-.4 1-1V3c0-.6-.4-1-1-1Z'), P('M8 4H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2M16 4h2a2 2 0 0 1 2 2v2M11 14h10'), P('m17 10 4 4-4 4')],
  link: [P('M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71'), P('M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71')],
  x: [P('M18 6 6 18'), P('m6 6 12 12')],
  check: [P('M20 6 9 17l-5-5')],
  checkCircle: [C(12, 12, 10), P('m9 12 2 2 4-4')],
  alert: [P('m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3'), P('M12 9v4'), P('M12 17h.01')],
  alertCircle: [C(12, 12, 10), L(12, 8, 12, 12), L(12, 16, 12.01, 16)],
  info: [C(12, 12, 10), P('M12 16v-4'), P('M12 8h.01')],
  folder: [P('M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z')],
  folderOpen: [P('m6 14 1.5-2.9A2 2 0 0 1 9.24 10H20a2 2 0 0 1 1.94 2.5l-1.54 6a2 2 0 0 1-1.95 1.5H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h3.9a2 2 0 0 1 1.69.9l.81 1.2a2 2 0 0 0 1.67.9H18a2 2 0 0 1 2 2v2')],
  play: [['polygon', { points: '6 3 20 12 6 21 6 3' }]],
  external: [P('M15 3h6v6'), P('M10 14 21 3'), P('M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6')],
  copy: [R(8, 8, 14, 14, 2), P('M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2')],
  trash: [P('M3 6h18'), P('M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6'), P('M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2'), L(10, 11, 10, 17), L(14, 11, 14, 17)],
  refresh: [P('M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8'), P('M21 3v5h-5'), P('M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16'), P('M8 16H3v5')],
  retry: [P('M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8'), P('M3 3v5h5')],
  search: [C(11, 11, 8), P('m21 21-4.3-4.3')],
  chevronDown: [P('m6 9 6 6 6-6')],
  chevronRight: [P('m9 18 6-6-6-6')],
  arrowRight: [P('M5 12h14'), P('m12 5 7 7-7 7')],
  arrowLeft: [P('m12 19-7-7 7-7'), P('M19 12H5')],
  more: [C(12, 12, 1), C(19, 12, 1), C(5, 12, 1)],
  film: [R(3, 3, 18, 18, 2), P('M7 3v18'), P('M3 7.5h4'), P('M3 12h18'), P('M3 16.5h4'), P('M17 3v18'), P('M17 7.5h4'), P('M17 16.5h4')],
  music: [P('M9 18V5l12-2v13'), C(6, 18, 3), C(18, 16, 3)],
  sparkles: [
    P('M9.937 15.5A2 2 0 0 0 8.5 14.063l-6.135-1.582a.5.5 0 0 1 0-.962L8.5 9.936A2 2 0 0 0 9.937 8.5l1.582-6.135a.5.5 0 0 1 .963 0L14.063 8.5A2 2 0 0 0 15.5 9.937l6.135 1.581a.5.5 0 0 1 0 .964L15.5 14.063a2 2 0 0 0-1.437 1.437l-1.582 6.135a.5.5 0 0 1-.963 0z'),
    P('M20 3v4'), P('M22 5h-4'), P('M4 17v2'), P('M5 18H3'),
  ],
  wrench: [P('M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z')],
  shield: [P('M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z'), P('m9 12 2 2 4-4')],
  sun: [C(12, 12, 4), P('M12 2v2'), P('M12 20v2'), P('m4.93 4.93 1.41 1.41'), P('m17.66 17.66 1.41 1.41'), P('M2 12h2'), P('M20 12h2'), P('m6.34 17.66-1.41 1.41'), P('m19.07 4.93-1.41 1.41')],
  moon: [P('M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z')],
  monitor: [R(2, 3, 20, 14, 2), L(8, 21, 16, 21), L(12, 17, 12, 21)],
  globe: [C(12, 12, 10), P('M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20'), P('M2 12h20')],
  zap: [P('M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z')],
  loader: [P('M21 12a9 9 0 1 1-6.219-8.56')],
  package: [P('m7.5 4.27 9 5.15'), P('M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z'), P('m3.3 7 8.7 5 8.7-5'), P('M12 22V12')],
  listVideo: [P('M12 12H3'), P('M16 6H3'), P('M12 18H3'), P('m16 12 5 3-5 3v-6Z')],
  clock: [C(12, 12, 10), ['polyline', { points: '12 6 12 12 16 14' }]],
  cookie: [P('M12 2a10 10 0 1 0 10 10 4 4 0 0 1-5-5 4 4 0 0 1-5-5'), P('M8.5 8.5v.01'), P('M16 15.5v.01'), P('M12 12v.01'), P('M11 17v.01'), P('M7 14v.01')],
  dropDown: [P('M12 17V3'), P('m6 11 6 6 6-6'), P('M19 21H5')],
  user: [P('M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2'), C(12, 7, 4)],
  hardDrive: [L(22, 12, 2, 12), P('M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z'), L(6, 16, 6.01, 16), L(10, 16, 10.01, 16)],
  book: [P('M12 7v14'), P('M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z')],
  keyboard: [R(2, 4, 20, 16, 2), P('M6 8h.001'), P('M10 8h.001'), P('M14 8h.001'), P('M18 8h.001'), P('M8 12h.001'), P('M12 12h.001'), P('M16 12h.001'), P('M7 16h10')],
  bug: [P('m8 2 1.88 1.88'), P('M14.12 3.88 16 2'), P('M9 7.13v-1a3.003 3.003 0 1 1 6 0v1'), P('M12 20c-3.3 0-6-2.7-6-6v-3a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v3c0 3.3-2.7 6-6 6'), P('M12 20v-9'), P('M6.53 9C4.6 8.8 3 7.1 3 5'), P('M6 13H2'), P('M3 21c0-2.1 1.7-3.9 3.8-4'), P('M20.97 5c0 2.1-1.6 3.8-3.5 4'), P('M22 13h-4'), P('M17.2 17c2.1.1 3.8 1.9 3.8 4')],
  heart: [P('M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z')],
  lock: [R(3, 11, 18, 11, 2), P('M7 11V7a5 5 0 0 1 10 0v4')],
  bell: [P('M10.268 21a2 2 0 0 0 3.464 0'), P('M3.262 15.326A1 1 0 0 0 4 17h16a1 1 0 0 0 .74-1.673C19.41 13.956 18 12.499 18 8A6 6 0 0 0 6 8c0 4.499-1.411 5.956-2.738 7.326')],
  megaphone: [P('m3 11 18-5v12L3 14v-3z'), P('M11.6 16.8a3 3 0 1 1-5.8-1.6')],
  gauge: [P('m12 14 4-4'), P('M3.34 19a10 10 0 1 1 17.32 0')],
  layers: [P('m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z'), P('m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65'), P('m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65')],
};

/** Returns a new <svg> element for the icon. Unknown names render an empty 24x24 box. */
export function icon(name, { size = 18, cls = '', strokeWidth = 2 } = {}) {
  const svg = document.createElementNS(SVG_NS, 'svg');
  svg.setAttribute('viewBox', '0 0 24 24');
  svg.setAttribute('width', String(size));
  svg.setAttribute('height', String(size));
  svg.setAttribute('fill', name === 'play' ? 'currentColor' : 'none');
  svg.setAttribute('stroke', 'currentColor');
  svg.setAttribute('stroke-width', String(strokeWidth));
  svg.setAttribute('stroke-linecap', 'round');
  svg.setAttribute('stroke-linejoin', 'round');
  svg.setAttribute('aria-hidden', 'true');
  svg.setAttribute('focusable', 'false');
  svg.setAttribute('class', `icon icon-${name}${cls ? ' ' + cls : ''}`);
  for (const [tag, attrs] of ICONS[name] || []) {
    const node = document.createElementNS(SVG_NS, tag);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, String(v));
    svg.appendChild(node);
  }
  return svg;
}

export function hasIcon(name) {
  return Object.prototype.hasOwnProperty.call(ICONS, name);
}
