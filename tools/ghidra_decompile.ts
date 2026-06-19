#!/usr/bin/env node

/**
 * Ghidra Decompiler Tool - TypeScript Wrapper (Refactored for OpenCode)
 * Decompiles binary functions using Ghidra's decompiler engine via FastAPI server.
 */

interface GhidraDecompileConfig {
  binary_path: string;
  function_address?: string;
  function_names?: string[];
  timeout?: number;
}

interface ToolResult {
  status: 'success' | 'error';
  tool_name: string;
  execution_time_ms: number;
  data: any;
  summary: string;
  metadata: { ai_next_step?: string; [key: string]: any };
}

async function runGhidraDecompile(config: GhidraDecompileConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    if (!config.binary_path) {
      throw new Error('binary_path is required');
    }

    const payload: Record<string, any> = {
      binary: config.binary_path,
      timeout: config.timeout || 300
    };

    if (config.function_address) payload.function_address = config.function_address;
    if (config.function_names && config.function_names.length > 0) {
      payload.function_names = config.function_names.join(',');
    }

    const apiUrl = 'http://tools:8000/decompile';
    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout((config.timeout || 300) * 1000)
      });
    } catch (fetchError) {
      const errorMsg = fetchError instanceof Error ? fetchError.message : String(fetchError);
      return {
        status: 'error', tool_name: 'ghidra_decompile',
        execution_time_ms: Date.now() - startTime,
        data: { error: errorMsg },
        summary: `Failed to connect to FastAPI server at ${apiUrl}: ${errorMsg}`,
        metadata: { ai_next_step: 'Ensure the tools container is running on http://tools:8000' }
      };
    }

    if (!response.ok) {
      let errorDetail = '';
      try {
        const errorBody = await response.json();
        errorDetail = errorBody.detail || JSON.stringify(errorBody);
      } catch {
        errorDetail = await response.text();
      }
      return {
        status: 'error', tool_name: 'ghidra_decompile',
        execution_time_ms: Date.now() - startTime,
        data: { error: `HTTP ${response.status}`, details: errorDetail },
        summary: `FastAPI server returned error: ${response.status} - ${errorDetail}`,
        metadata: { ai_next_step: 'Check binary file format and Ghidra installation on tools container' }
      };
    }

    let responseData;
    try {
      responseData = await response.json();
    } catch {
      const rawText = await response.text();
      return {
        status: 'error', tool_name: 'ghidra_decompile',
        execution_time_ms: Date.now() - startTime,
        data: { raw: rawText },
        summary: 'Failed to parse FastAPI response as JSON',
        metadata: { ai_next_step: 'Check server logs for decompilation errors' }
      };
    }

    return {
      status: 'success',
      tool_name: 'ghidra_decompile',
      execution_time_ms: Date.now() - startTime,
      data: responseData,
      summary: `Successfully decompiled ${config.function_address || config.function_names?.join(', ') || 'all functions'} from ${config.binary_path}`,
      metadata: {
        ai_next_step: 'Review decompiled code; analyze changes and security implications'
      }
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      status: 'error', tool_name: 'ghidra_decompile',
      execution_time_ms: Date.now() - startTime,
      data: { error: message },
      summary: `Ghidra decompiler error: ${message}`,
      metadata: { ai_next_step: 'Fix configuration and retry' }
    };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: GhidraDecompileConfig = { binary_path: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary': config.binary_path = args[++i]; break;
      case '--function-address': config.function_address = args[++i]; break;
      case '--function-names': config.function_names = args[++i].split(','); break;
      case '--timeout': config.timeout = parseInt(args[++i], 10); break;
    }
  }

  const result = await runGhidraDecompile(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(JSON.stringify({
      status: 'error', tool_name: 'ghidra_decompile', execution_time_ms: 0,
      data: { error: err.message },
      summary: `Fatal error: ${err.message}`,
      metadata: { ai_next_step: 'Check logs' }
    }, null, 2));
    process.exit(1);
  });
}

export { runGhidraDecompile, GhidraDecompileConfig, ToolResult };