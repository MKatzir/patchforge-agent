#!/usr/bin/env node

/**
 * Compiler Tool - TypeScript Wrapper
 * Compiles C/C++ source code with GCC/G++ for testing and exploit verification
 */

import * as fs from 'fs';
import * as path from 'path';
import * as childProcess from 'child_process';

interface CompilerConfig {
  source_path: string;
  output_path?: string;
  compiler?: 'gcc' | 'g++';
  flags?: string[];
  optimization_level?: 'O0' | 'O1' | 'O2' | 'O3' | 'Os';
  arch?: string;
  output_format?: 'json' | 'text';
}

interface ToolResult {
  status: 'success' | 'error';
  tool_name: string;
  execution_time_ms: number;
  data: any;
  summary: string;
  metadata: {
    ai_next_step?: string;
    [key: string]: any;
  };
}

async function runCompiler(config: CompilerConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    if (!config.source_path) {
      throw new Error('source_path is required');
    }

    if (!fs.existsSync(config.source_path)) {
      throw new Error(`Source file not found: ${config.source_path}`);
    }

    const pythonScriptPath = path.join(__dirname, 'compiler.py');
    const args = [
      pythonScriptPath,
      '--source', config.source_path,
    ];

    if (config.output_path) args.push('--output', config.output_path);
    if (config.compiler) args.push('--compiler', config.compiler);
    if (config.flags) args.push('--flags', config.flags.join(' '));
    if (config.optimization_level) args.push('--optimization', config.optimization_level);
    if (config.arch) args.push('--arch', config.arch);
    args.push('--output-format', config.output_format || 'json');

    return new Promise((resolve) => {
      const proc = childProcess.spawn('python3', args, {
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stdout = '';
      let stderr = '';

      proc.stdout?.on('data', (data) => { stdout += data.toString(); });
      proc.stderr?.on('data', (data) => { stderr += data.toString(); });

      proc.on('close', (code) => {
        const executionTime = Date.now() - startTime;

        if (code !== 0) {
          const result: ToolResult = {
            status: 'error',
            tool_name: 'compiler',
            execution_time_ms: executionTime,
            data: { stderr },
            summary: `Compilation failed: ${stderr || stdout}`,
            metadata: { ai_next_step: 'Fix source code errors and retry' }
          };
          try {
            const parsed = JSON.parse(stdout);
            if (parsed.error || parsed.summary) {
              result.data = parsed;
              result.summary = parsed.summary || result.summary;
            }
          } catch (_) {}
          resolve(result);
          return;
        }

        try {
          const result = JSON.parse(stdout);
          result.status = 'success';
          result.tool_name = 'compiler';
          result.execution_time_ms = executionTime;
          result.metadata = result.metadata || {};
          result.metadata.ai_next_step = 'Binary compiled; pass to BinDiff or test with exploit';
          resolve(result);
        } catch (e) {
          resolve({
            status: 'error',
            tool_name: 'compiler',
            execution_time_ms: executionTime,
            data: { stdout, stderr },
            summary: 'Failed to parse compiler output',
            metadata: { ai_next_step: 'Check Python script implementation' }
          });
        }
      });
    });
  } catch (error) {
    const executionTime = Date.now() - startTime;
    const message = error instanceof Error ? error.message : String(error);
    return {
      status: 'error',
      tool_name: 'compiler',
      execution_time_ms: executionTime,
      data: { error: message },
      summary: `Compiler error: ${message}`,
      metadata: { ai_next_step: 'Fix configuration and retry' }
    };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: CompilerConfig = {
    source_path: '',
    output_format: 'json',
    compiler: 'gcc',
    optimization_level: 'O0'
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--source': config.source_path = args[++i]; break;
      case '--output': config.output_path = args[++i]; break;
      case '--compiler': config.compiler = args[++i] as 'gcc' | 'g++'; break;
      case '--flags': config.flags = args[++i].split(' '); break;
      case '--optimization': config.optimization_level = args[++i] as any; break;
      case '--arch': config.arch = args[++i]; break;
      case '--output-format': config.output_format = args[++i] as 'json' | 'text'; break;
    }
  }

  const result = await runCompiler(config);
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
