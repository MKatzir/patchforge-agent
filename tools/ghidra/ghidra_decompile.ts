#!/usr/bin/env node
interface DecompileConfig {
  binary: string;
  function_address?: string;
  function_names?: string;
  ignore_cache?: boolean;
}

async function runDecompile(config: DecompileConfig) {
  // MIDDLEWARE PATH TRANSLATION
  const payload = {
    binary: config.binary.replace(/^\/app\//, '/work/'),
    function_address: config.function_address,
    function_names: config.function_names,
    ignore_cache: config.ignore_cache || false
  };

  try {
    const response = await fetch('http://tools:8000/decompile', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(300000)
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    
    return {
      status: 'success',
      tool_name: 'ghidra_decompile',
      data: data,
      summary: `Successfully decompiled ${config.function_address || config.function_names} from ${config.binary}`,
      metadata: { ai_next_step: 'Review decompiled C code' }
    };
  } catch (error) {
    return { status: 'error', data: { error: String(error) } };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: DecompileConfig = { binary: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary': config.binary = args[++i]; break;
      case '--function-address': config.function_address = args[++i]; break;
      case '--function-names': config.function_names = args[++i]; break;
      case '--ignore-cache': config.ignore_cache = true; break;
    }
  }
  const result = await runDecompile(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) { main(); }
export { runDecompile, DecompileConfig };
