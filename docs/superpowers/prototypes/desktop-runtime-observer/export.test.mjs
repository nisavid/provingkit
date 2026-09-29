import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, readFile, readdir, rm, stat } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { replaceExport } from './export.mjs';
import { createObserver, inspectEnvelope } from './observer.mjs';
import { createFixture } from './fixture.mjs';

test('a selected synthetic file is replaced by complete newer JSON and read through the same envelope seam', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'observer-synthetic-'));
  const file = join(directory, 'observation.json');
  try {
    const f = createFixture();
    const observer = createObserver({ selectReceiver: f.selectReceiver });
    const first = await observer.observeReceiver(f.binding);
    await replaceExport(file, first);
    f.record.host.alwaysAllowedReasons.push('fixture-change');
    const second = await observer.observeReceiver(f.binding);
    await replaceExport(file, second);
    const result = inspectEnvelope(await readFile(file, 'utf8'), f.binding, { afterSequence: first.sequence });
    assert.equal(result.state, 'usable-partial');
    assert.deepEqual(result.envelope.fields.hostAfter.value.alwaysAllowedReasons, ['fixture-change']);
    assert.equal((await stat(file)).mode & 0o777, 0o600);
    assert.deepEqual(await readdir(directory), ['observation.json']);
    const incompatible = await observer.observeReceiver(f.binding, {compatibility:{
      export:{state:'incompatible',basis:'Synthetic exporter failure.'},
    }});
    await assert.rejects(replaceExport(file, incompatible), /incompatible export/);
    assert.equal(JSON.parse(await readFile(file,'utf8')).sequence, second.sequence);
  } finally { await rm(directory, { recursive: true, force: true }); }
});
