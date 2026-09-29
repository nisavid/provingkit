// Static data inspection only: never imports or executes a Desktop module.
import { readFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { join } from 'node:path';
const directory = process.argv[2];
if (!directory) throw new Error('Supply the directory containing the two extracted build files.');
const plan = JSON.parse(await readFile(new URL('insertion-points.json', import.meta.url), 'utf8'));
for (const source of plan.sources) {
  const bytes = await readFile(join(directory, source.file));
  if (createHash('sha256').update(bytes).digest('hex') !== source.sha256)
    throw new Error(`${source.file}: changed source needs assessment; this is not a finding of incompatibility.`);
  for (const anchor of source.anchors) {
    const needle = Buffer.from(anchor.text);
    if (bytes.indexOf(needle) !== anchor.byte_offset || bytes.lastIndexOf(needle) !== anchor.byte_offset)
      throw new Error(`${source.file}: reassess ${anchor.purpose}.`);
  }
  console.log(`${source.file}: ${source.anchors.length} unique anchors match the inspected source.`);
}
