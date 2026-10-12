// Reuse one REA MCP session for a caller-supplied local analysis plan.
// Raw outputs must remain under ignored analysis/private/.
import { createRequire } from 'node:module';
import { homedir } from 'node:os';
import path from 'node:path';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createWriteStream } from 'node:fs';
import { fileURLToPath } from 'node:url';

const repository = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const toolRoot = process.env.ULTRASUN_TOOL_ROOT || path.join(homedir(), '.local/share/ultrasunnymoon');
const require = createRequire(path.join(toolRoot, 'rea-source/package.json'));
const { Client } = require('@modelcontextprotocol/client');
const { StdioClientTransport } = require('@modelcontextprotocol/client/stdio');
const plan = JSON.parse(await readFile(process.argv[2], 'utf8'));
const run = process.argv[3] || `${plan.run}-${new Date().toISOString().replaceAll(':', '-')}`;
const output = path.resolve(repository, 'analysis/private', run);
if (!output.startsWith(path.join(repository, 'analysis/private') + path.sep)) {
  throw new Error('Output must remain under analysis/private/');
}
await mkdir(path.dirname(output), { recursive: true });
await mkdir(output); // Refuse to overwrite an earlier run's evidence.
console.log(JSON.stringify({ output }));
const transport = new StdioClientTransport({ command: 'bash',
  args: [path.join(repository, 'tools/rea-arm-full.sh'), 'mcp'], stderr: 'pipe' });
const client = new Client({ name: 'ultrasunnymoon-analysis', version: '0.1.0' });
const started = performance.now();
const log = createWriteStream(path.join(output, 'server.log'));
const timings = [];
let targetOpen = false;
try {
  transport.stderr?.pipe(log);
  await client.connect(transport);
  const catalog = await client.listTools();
  await writeFile(path.join(output, 'catalog.json'), JSON.stringify(catalog, null, 2));
  const available = new Set(catalog.tools.map(tool => tool.name));
  for (let index = 0; index < (plan.calls || []).length; index++) {
    const call = plan.calls[index];
    if (!available.has(call.name)) throw new Error(`Unadvertised tool: ${call.name}`);
    const arguments_ = { ...(call.arguments || {}) };
    if (call.name === 'open_binary') arguments_.path = path.resolve(repository, arguments_.path);
    const start = performance.now();
    const result = await client.callTool({ name: call.name, arguments: arguments_ },
      { timeout: 600000 });
    await writeFile(path.join(output, `${index}-${call.name}.json`), JSON.stringify(result, null, 2));
    const timing = { tool: call.name, seconds: (performance.now()-start)/1000, isError: Boolean(result.isError) };
    timings.push(timing);
    console.log(JSON.stringify(timing));
    if (result.isError) throw new Error(`REA tool ${call.name} failed; see private evidence`);
    if (call.name === 'open_binary') targetOpen = true;
    if (call.name === 'close_binary') targetOpen = false;
  }
  await writeFile(path.join(output, 'timing.json'), JSON.stringify({ seconds: (performance.now()-started)/1000, calls: timings }, null, 2));
} finally {
  if (targetOpen) {
    try { await client.callTool({ name: 'close_binary', arguments: {} }, { timeout: 30000 }); }
    catch { console.error('Could not verify target cleanup; inspect private server log.'); }
  }
  await client.close();
  log.end();
}
