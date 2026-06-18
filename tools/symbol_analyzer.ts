#!/usr/bin/env node

/**
 * Symbol Analyzer Tool - TypeScript Wrapper (Refactored for OpenCode)
 * Extracts and analyzes symbols from binaries via FastAPI server.
 * 
 * This wrapper communicates with the FastAPI job server (http://tools:8000) instead
 * of spawning child processes. It sends HTTP requests and parses responses.
 * 
 * NOTE: Requires /symbol_analyzer endpoint on FastAPI server.
 */

interface SymbolAnalyzerConfig {
  binary_path: string;
  symbol_types?: string;
  demangle?: boolean;
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

async function runSymbolAnalyzer(config: SymbolAnalyzerConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    if (!config.binary_path) {
      throw new Error('binary_path is required');
    }

    // Build request payload
    const payload: Record<string, any> = {
      binary: config.binary_path
    };

    if (config.symbol_types) {
      payload.symbol_types = config.symbol_types;
    }

    if (config.demangle !== undefined) {
      payload.demangle = config.demangle;
    }

    // Call FastAPI server at http://tools:8000/symbol_analyzer
    const apiUrl = 'http://tools:8000/symbol_analyzer';
    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000)
      });
    } catch (fetchError) {
      const errorMsg = fetchError instanceof Error ? fetchError.message : String(fetchError);
      const executionTime = Date.now() - startTime;
      return {
        status: 'error',
        tool_name: 'symbol_analyzer',
        execution_time_ms: executionTime,
        data: { error: errorMsg },
        summary: `Failed to connect to FastAPI server at ${apiUrl}: ${errorMsg}`,
        metadata: {
          ai_next_step: 'Ensure the tools container is running on http://tools:8000'
        }
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

      const executionTime = Date.now() - startTime;
      return {
        status: 'error',
        tool_name: 'symbol_analyzer',
        execution_time_ms: executionTime,
        data: { error: `HTTP ${response.status}`, details: errorDetail },
        summary: `FastAPI server returned error: ${response.status} - ${errorDetail}`,
        metadata: {
          ai_next_step: 'Verify binary file exists and is in a supported format'
        }
      };
    }

    let responseData;
    try {
      responseData = await response.json();
    } catch {
      const executionTime = Date.now() - startTime;
      const rawText = await response.text();
      return {
        status: 'error',
        tool_name: 'symbol_analyzer',
        execution_time_ms: executionTime,
        data: { raw: rawText },
        summary: 'Failed to parse FastAPI response as JSON',
        metadata: {
          ai_next_step: 'Check server logs for symbol extraction errors'
        }
      };
    }

    const executionTime = Date.now() - startTime;

    // Build successful result
    return {
      status: 'success',
      tool_name: 'symbol_analyzer',
      execution_time_ms: executionTime,
      data: responseData,
      summary: `Successfully extracted symbols from ${config.binary_path} (${responseData.count || '?'} symbols found)`,
      metadata: {
        ai_next_step: 'Review symbols for changed functions; correlate with BinDiff and disassembly results'
      }
    };
  } catch (error) {
    const executionTime = Date.now() - startTime;
    const message = error instanceof Error ? error.message : String(error);

    return {
      status: 'error',
      tool_name: 'symbol_analyzer',
      execution_time_ms: executionTime,
      data: { error: message },
      summary: `Symbol analyzer error: ${message}`,
      metadata: {
        ai_next_step: 'Check configuration and ensure binary file is valid'
      }
    };
  }
}

// CLI interface for direct invocation
async function main() {
  const args = process.argv.slice(2);
  const config: SymbolAnalyzerConfig = {
    binary_path: ''
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary':
        config.binary_path = args[++i];
        break;
      case '--symbol-types':
        config.symbol_types = args[++i];
        break;
      case '--demangle':
        config.demangle = true;
        break;
    }
  }

  const result = await runSymbolAnalyzer(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(JSON.stringify({
      status: 'error',
      tool_name: 'symbol_analyzer',
      execution_time_ms: 0,
      data: { error: err.message },
      summary: `Fatal error: ${err.message}`,
      metadata: { ai_next_step: 'Check logs' }
    }, null, 2));
    process.exit(1);
  });
}

export { runSymbolAnalyzer, SymbolAnalyzerConfig, ToolResult };


async function main() {
  const args = process.argv.slice(2);
  const config: SymbolAnalyzerConfig = {
    binary_path: '',
    demangle: true,
    output_format: 'json'
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary': config.binary_path = args[++i]; break;
      case '--symbol-types': config.symbol_types = args[++i]; break;
      case '--demangle': config.demangle = true; break;
      case '--output-format': config.output_format = args[++i] as 'json' | 'text'; break;
    }
  }

  const result = await runSymbolAnalyzer(config);
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
