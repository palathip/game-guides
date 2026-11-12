import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';

const path = fileURLToPath(new URL('../template/state.js', import.meta.url));
const sandbox = {};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(path, 'utf8'), sandbox);
const S = sandbox.GGState;

const A = '2020-01-02T00:00:00.000Z';
const B = '2024-05-01T00:00:00.000Z';
const C = '2024-06-01T00:00:00.000Z';

test('theme choice follows system until the user picks light or dark', () => {
  assert.equal(S.themeChoice('light'), 'light');
  assert.equal(S.themeChoice('dark'), 'dark');
  for (const raw of [null, undefined, '', 'system', 'LIGHT', 'auto']) assert.equal(S.themeChoice(raw), null);
  assert.equal(S.activeTheme(null, true), 'dark');
  assert.equal(S.activeTheme(null, false), 'light');
  assert.equal(S.activeTheme('light', true), 'light');
  assert.equal(S.toggleTheme(null, true), 'light');
  assert.equal(S.toggleTheme(null, false), 'dark');
  assert.equal(S.toggleTheme('light', true), 'dark');
  assert.equal(S.toggleTheme('dark', false), 'light');
  assert.equal(S.toggleTheme('nope', true), 'light');
});

test('cleared merge unions dates and does not mutate inputs', () => {
  const local = {b3guide: B, bad: 'yesterday'};
  const remote = {ffxintl: A, b3guide: C, nope: 'x'};
  const merged = S.mergeCleared(local, remote);
  assert.equal(merged.b3guide, B);
  assert.equal(merged.ffxintl, A);
  assert.equal(merged.bad, undefined);
  assert.equal(merged.nope, undefined);
  assert.deepEqual(local, {b3guide: B, bad: 'yesterday'});
  assert.equal(remote.nope, 'x');
});

test('cleared write replaces one slug and leaves checklist keys alone', () => {
  const doc = {
    b3guide: ['a', 'b'],
    ffxintl: ['z'],
    _cleared: {ffxintl: A, nope: 'x'},
  };
  const snapshot = JSON.parse(JSON.stringify(doc));
  const on = S.writeCleared(doc, 'b3guide', B);
  assert.deepEqual(on.b3guide, ['a', 'b']);
  assert.deepEqual(on.ffxintl, ['z']);
  assert.equal(on._cleared.ffxintl, A);
  assert.equal(on._cleared.nope, 'x');
  assert.equal(on._cleared.b3guide, B);
  assert.deepEqual(doc, snapshot);

  const off = S.writeCleared(on, 'b3guide', null);
  assert.equal(off._cleared.b3guide, undefined);
  assert.equal(off._cleared.ffxintl, A);
  assert.equal(off._cleared.nope, 'x');
  assert.deepEqual(off.b3guide, ['a', 'b']);
  assert.equal(on._cleared.b3guide, B);

  const check = S.writeChecklist(off, 'b3guide', ['only']);
  assert.deepEqual(check.b3guide, ['only']);
  assert.deepEqual(check.ffxintl, ['z']);
  assert.equal(check._cleared.ffxintl, A);
  assert.equal(check._cleared.nope, 'x');
  assert.deepEqual(off.b3guide, ['a', 'b']);
  assert.equal(S.writeCleared(doc, 'b3guide', 'not-a-date')._cleared.b3guide, undefined);
  assert.equal(S.writeChecklist(doc, '_cleared', ['nope'])._cleared.ffxintl, A);
});

test('sync config is the one gist and checklist.json is the only file', () => {
  assert.equal(S.SYNC_KEY, 'gg-sync');
  assert.equal(S.CLEARED_KEY, 'gg-cleared');
  assert.equal(S.THEME_KEY, 'gg-theme');
  assert.equal(S.FILE, 'checklist.json');
  assert.equal(S.RESERVED, '_cleared');
  assert.equal(S.slugOf('b3guide:'), 'b3guide');
  assert.equal(S.slugOf('totkguide:'), 'totkguide');
  const id = '0123456789abcdef0123';
  const tok = 'a'.repeat(24);
  const c = S.syncConfig(JSON.stringify({id, tok, extra: 'no'}));
  assert.equal(c.id, id);
  assert.equal(c.tok, tok);
  assert.equal(c.extra, undefined);
  assert.equal(S.syncConfig(JSON.stringify({id, tok: 'short'})), null);
  assert.equal(S.syncConfig('{'), null);
});
