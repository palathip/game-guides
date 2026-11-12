/* Shared theme + checklist/cleared state. No tokens are logged.
   Gist file is always checklist.json. Cleared dates live under the reserved
   key _cleared so per-game checklist arrays stay intact.
   Theme switch visuals follow data-theme in CSS (pill track, round knob,
   1.75 stroke sun/moon). This file only persists the choice and exposes state. */
(function (root) {
  const THEME_KEY = 'gg-theme';
  const CLEARED_KEY = 'gg-cleared';
  const SYNC_KEY = 'gg-sync';
  const FILE = 'checklist.json';
  const RESERVED = '_cleared';
  const API = 'https://api.github.com/gists/';
  const ID_RE = /^[0-9a-f]{20,40}$/i;
  const TK_RE = /^[A-Za-z0-9_]{20,255}$/;
  const SLUG_RE = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
  const ISO_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?Z$/;
  const SKIP = new Set(['__proto__', 'constructor', 'prototype']);

  function themeChoice(raw) {
    return raw === 'light' || raw === 'dark' ? raw : null;
  }
  function activeTheme(stored, systemDark) {
    return themeChoice(stored) || (systemDark ? 'dark' : 'light');
  }
  function toggleTheme(stored, systemDark) {
    return activeTheme(stored, systemDark) === 'dark' ? 'light' : 'dark';
  }
  function slugOf(storageKey) {
    return String(storageKey || '').replace(/[^\w-]+$/, '') || 'guide';
  }
  function isPlain(v) {
    return !!v && typeof v === 'object' && !Array.isArray(v);
  }
  function isIso(v) {
    return typeof v === 'string' && ISO_RE.test(v) && !Number.isNaN(Date.parse(v));
  }
  function syncConfig(raw) {
    try {
      const c = JSON.parse(raw || 'null');
      if (!c || typeof c !== 'object' || Array.isArray(c) || !ID_RE.test(c.id) || !TK_RE.test(c.tok)) return null;
      return {id: c.id, tok: c.tok};
    } catch (e) { return null; }
  }
  function normCleared(v) {
    const o = {};
    if (!isPlain(v)) return o;
    for (const k of Object.keys(v)) {
      if (SKIP.has(k) || k === RESERVED || !SLUG_RE.test(k)) continue;
      if (isIso(v[k])) o[k] = v[k];
    }
    return o;
  }
  /* Union: a slug stays if either side has a valid date. Both dates -> the earlier one. */
  function mergeCleared(local, remote) {
    const a = normCleared(local), b = normCleared(remote), o = {};
    for (const k of Object.keys(a)) o[k] = a[k];
    for (const k of Object.keys(b)) if (!o[k] || b[k] < o[k]) o[k] = b[k];
    return o;
  }
  function copyDoc(doc) {
    const src = isPlain(doc) ? doc : {};
    const next = {};
    for (const k of Object.keys(src)) {
      if (SKIP.has(k)) continue;
      const v = src[k];
      if (Array.isArray(v)) next[k] = v.slice();
      else if (k === RESERVED && isPlain(v)) {
        const m = {};
        for (const ck of Object.keys(v)) if (!SKIP.has(ck)) m[ck] = v[ck];
        next[k] = m;
      } else next[k] = v;
    }
    return next;
  }
  /* Replace only _cleared[slug]. Other checklist keys and other slugs are copied through. */
  function writeCleared(doc, slug, iso) {
    const next = copyDoc(doc);
    if (!SLUG_RE.test(slug) || slug === RESERVED) return next;
    const raw = isPlain(doc) ? doc[RESERVED] : null;
    const map = {};
    if (isPlain(raw)) for (const k of Object.keys(raw)) if (!SKIP.has(k)) map[k] = raw[k];
    if (iso == null || iso === '') delete map[slug];
    else if (isIso(iso)) map[slug] = iso;
    else return next;
    if (Object.keys(map).length) next[RESERVED] = map;
    else delete next[RESERVED];
    return next;
  }
  /* Replace only this game's checklist array. _cleared is copied, not rebuilt. */
  function writeChecklist(doc, slug, keys) {
    const next = copyDoc(doc);
    if (!SLUG_RE.test(slug) || slug === RESERVED) return next;
    next[slug] = (Array.isArray(keys) ? keys : []).filter(k => typeof k === 'string');
    return next;
  }
  function headers(c) {
    return {Authorization: 'Bearer ' + c.tok, Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'};
  }
  async function gistRead(c) {
    const r = await fetch(API + c.id, {headers: headers(c), cache: 'no-store'});
    if (!r.ok) throw r.status;
    const j = await r.json();
    const f = j.files && j.files[FILE];
    if (!f || f.truncated) throw 'nofile';
    let o;
    try { o = JSON.parse(f.content || '{}'); } catch (e) { throw 'json'; }
    return isPlain(o) ? o : {};
  }
  async function gistWrite(c, obj) {
    const r = await fetch(API + c.id, {
      method: 'PATCH',
      headers: Object.assign({'Content-Type': 'application/json'}, headers(c)),
      body: JSON.stringify({files: {[FILE]: {content: JSON.stringify(obj, null, 1)}}})
    });
    if (!r.ok) throw r.status;
  }
  /* Home page: read local, then union the Gist into localStorage. Never PATCH. */
  async function pullCleared(storage) {
    const store = storage || (typeof localStorage !== 'undefined' ? localStorage : null);
    if (!store) return null;
    let raw = null;
    try { raw = store.getItem(SYNC_KEY); } catch (e) { return null; }
    const c = syncConfig(raw);
    if (!c) return null;
    let doc;
    try { doc = await gistRead(c); } catch (e) { return null; }
    let local = {};
    try { local = normCleared(JSON.parse(store.getItem(CLEARED_KEY) || '{}')); } catch (e) { local = {}; }
    const merged = mergeCleared(local, doc[RESERVED]);
    try { store.setItem(CLEARED_KEY, JSON.stringify(merged)); } catch (e) {}
    return merged;
  }
  function bindThemeSwitch(btn) {
    if (!btn || typeof document === 'undefined' || typeof matchMedia !== 'function') return;
    const systemDark = () => matchMedia('(prefers-color-scheme: dark)').matches;
    const readStored = () => { try { return localStorage.getItem(THEME_KEY); } catch (e) { return null; } };
    const paint = () => {
      const dark = activeTheme(readStored(), systemDark()) === 'dark';
      btn.setAttribute('aria-checked', dark ? 'true' : 'false');
      const lab = document.getElementById('thml');
      if (lab) lab.textContent = dark ? 'ธีมมืด' : 'ธีมสว่าง';
    };
    const apply = theme => {
      document.documentElement.setAttribute('data-theme', theme);
      try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
      let m = document.getElementById('gg-tc');
      if (!m) { m = document.createElement('meta'); m.id = 'gg-tc'; m.setAttribute('name', 'theme-color'); }
      m.setAttribute('content', theme === 'dark' ? '#000000' : '#f5f5f7');
      document.head.appendChild(m);
      paint();
    };
    paint();
    btn.addEventListener('click', () => apply(toggleTheme(readStored(), systemDark())));
    const mq = matchMedia('(prefers-color-scheme: dark)');
    if (mq.addEventListener) mq.addEventListener('change', () => { if (!themeChoice(readStored())) paint(); });
    requestAnimationFrame(() => document.documentElement.classList.add('thm-ready'));
  }

  root.GGState = {
    THEME_KEY, CLEARED_KEY, SYNC_KEY, FILE, RESERVED, ID_RE, TK_RE,
    themeChoice, activeTheme, toggleTheme, slugOf, syncConfig, normCleared, mergeCleared,
    writeCleared, writeChecklist, gistRead, gistWrite, pullCleared, bindThemeSwitch
  };
})(typeof globalThis !== 'undefined' ? globalThis : this);
