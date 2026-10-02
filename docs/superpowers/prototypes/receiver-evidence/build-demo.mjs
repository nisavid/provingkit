import { readFile, writeFile } from 'node:fs/promises';

const file = name => new URL(name, import.meta.url);
let page = await readFile(file('demo-source.html'), 'utf8');
const code = await Promise.all(['reader.mjs', 'hook.mjs', 'fixtures.mjs'].map(name => readFile(file(name), 'utf8')));
// Embed the tested pure functions verbatim apart from ES module export syntax.
page = page.replace('/* INLINE_MODULES */', () => code.map(s => s.replace(/^export /gm, '')).join('\n'));
await writeFile(file('demo.html'), page);
