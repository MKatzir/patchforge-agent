#!/usr/bin/env node
interface BinDiffConfig {
  before_binary: string;
  after_binary: string;
  similarity_threshold?: number;
  min_block_size?: number;
  opcode_only?: boolean;
}

async function runBinDiff(config: BinDiffConfig) {
  // MIDDLEWARE PATH TRANSLATION
  const payload = {
    before: config.before_binary.replace(/^\/app\//, '/work/'),
    after: config.after_binary.replace(/^\/app\//, '/work/'),
    similarity_threshold: config.similarity_threshold || 0.95,
    min_block_size: config.min_block_size || 10,
    opcode_only: config.opcode_only || false
  };

  try {
    const response = await fetch('http://tools:8000/bindiff', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(120000)
    });
    
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json();
    
    return {
      status: 'success',
      tool_name: 'bindiff',
      data: data,
      summary: data.summary || `Compared binaries`,
      metadata: data.metadata || {}
    };
  } catch (error) {
    return { status: 'error', data: { error: String(error) } };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: BinDiffConfig = { before_binary: '', after_binary: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--before': config.before_binary = args[++i]; break;
      case '--after': config.after_binary = args[++i]; break;
      case '--similarity-threshold': config.similarity_threshold = parseFloat(args[++i]); break;
      case '--min-block-size': config.min_block_size = parseInt(args[++i]); break;
      case '--opcode-only': config.opcode_only = true; break;
    }
  }
  const result = await runBinDiff(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) { main(); }
export { runBinDiff, BinDiffConfig };
