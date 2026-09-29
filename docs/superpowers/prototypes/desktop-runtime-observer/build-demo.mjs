import { readFile, writeFile } from 'node:fs/promises';
const file = name => new URL(name, import.meta.url);
let html = await readFile(file('demo-shell.html'), 'utf8');
for (const [marker, name] of [['OBSERVER','observer.mjs'],['FIXTURE','fixture.mjs']]) {
  const source = (await readFile(file(name),'utf8')).replaceAll('export function ', 'function ').replaceAll('</script', '<\\/script');
  html = html.replace(`/*__${marker}__*/`, () => source);
}
if (process.argv.includes('--check')) {
  if (html !== await readFile(file('demo.html'), 'utf8')) throw new Error('demo.html differs from its source; run build-demo.mjs');
  console.log('Standalone demo matches the tested modules.');
} else await writeFile(file('demo.html'),html);
