#!/usr/bin/env node

/**
 * Ghidra Disassembler Tool - TypeScript Wrapper (Refactored for OpenCode)
 * Disassembles binary files using Ghidra's headless analyzer via FastAPI server.
 * 
 * This wrapper communicates with the FastAPI job server (http://tools:8000) instead
 * of spawning child processes. It sends HTTP requests and parses responses.
 */

interface GhidraDisasmConfig {
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
  metadata: {
    ai_next_step?: string;
    [key: string]: any;
  };
}

async function runGhidraDisasm(config: GhidraDisasmConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    // Validate inputs
    if (!config.binary_path) {
      throw new Error('binary_path is required');
    }

    // Build request payload matching FuncRequest model in job_server.py
    const payload: Record<string, any> = {
      binary: config.binary_path,
      timeout: config.timeout || 300
    };

    if (config.function_address) {
      payload.function_address = config.function_address;
    }

    if (config.function_names && config.function_names.length > 0) {
      payload.function_names = config.function_names.join(',');
    }

    // Call FastAPI server at http://tools:8000/disasm
    const apiUrl = 'http://tools:8000/disasm';
    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout((config.timeout || 300) * 1000)
      });
    } catch (fetchError) {
      const errorMsg = fetchError instanceof Error ? fetchError.message : String(fetchError);
      const executionTime = Date.now() - startTime;
      return {
        status: 'error',
        tool_name: 'ghidra_disasm',
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
        tool_name: 'ghidra_disasm',
        execution_time_ms: executionTime,
        data: { error: `HTTP ${response.status}`, details: errorDetail },
        summary: `FastAPI server returned error: ${response.status} - ${errorDetail}`,
        metadata: {
          ai_next_step: 'Check binary file format and Ghidra installation on tools container'
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
        tool_name: 'ghidra_disasm',
        execution_time_ms: executionTime,
        data: { raw: rawText },
        summary: 'Failed to parse FastAPI response as JSON',
        metadata: {
          ai_next_step: 'Check server logs for disassembly errors'
        }
      };
    }

    const executionTime = Date.now() - startTime;

    // Build successful result
    return {
      status: 'success',
      tool_name: 'ghidra_disasm',
      execution_time_ms: executionTime,
      data: responseData,
      summary: `Successfully disassembled ${config.function_address || config.function_names?.join(', ') || 'all functions'} from ${config.binary_path}`,
      metadata: {
        ai_next_step: 'Review assembly instructions; compare with before/after versions for changes'
      }
    };
  } catch (error) {
    const executionTime = Date.now() - startTime;
    const message = error instanceof Error ? error.message : String(error);

    return {
      status: 'error',
      tool_name: 'ghidra_disasm',
      execution_time_ms: executionTime,
      data: { error: message },
      summary: `Ghidra disassembler error: ${message}`,
      metadata: {
        ai_next_step: 'Fix configuration (binary path, function addresses) and retry'
      }
    };
  }
}

// CLI interface for direct invocation
async function main() {
  const args = process.argv.slice(2);
  const config: GhidraDisasmConfig = {
    binary_path: ''
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary':
        config.binary_path = args[++i];
        break;
      case '--function-address':
        config.function_address = args[++i];
        break;
      case '--function-names':
        config.function_names = args[++i].split(',');
        break;
      case '--timeout':
        config.timeout = parseInt(args[++i], 10);
        break;
    }
  }

  const result = await runGhidraDisasm(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(JSON.stringify({
      status: 'error',
      tool_name: 'ghidra_disasm',
      execution_time_ms: 0,
      data: { error: err.message },
      summary: `Fatal error: ${err.message}`,
      metadata: { ai_next_step: 'Check logs' }
    }, null, 2));
    process.exit(1);
  });
}

export { runGhidraDisasm, GhidraDisasmConfig, ToolResult };

        } catch (e) {
          resolve({
            status: 'error',
            tool_name: 'ghidra_disasm',
            execution_time_ms: executionTime,
            data: { stdout, stderr },
            summary: 'Failed to parse Ghidra disassembly output',
            metadata: {
              ai_next_step: 'Check Python script implementation'
            }
          });
        }
      });
    });
  } catch (error) {
    const executionTime = Date.now() - startTime;
    const message = error instanceof Error ? error.message : String(error);

    return {
      status: 'error',
      tool_name: 'ghidra_disasm',
      execution_time_ms: executionTime,
      data: { error: message },
      summary: `Ghidra disassembler error: ${message}`,
      metadata: {
        ai_next_step: 'Fix configuration and retry'
      }
    };
  }
}

// CLI interface
async function main() {
  const args = process.argv.slice(2);
  const config: GhidraDisasmConfig = {
    binary_path: '',
    output_format: 'json'
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary':
        config.binary_path = args[++i];
        break;
      case '--function-address':
        config.function_address = args[++i];
        break;
      case '--function-names':
        config.function_names = args[++i].split(',');
        break;
      case '--output-format':
        config.output_format = args[++i] as 'json' | 'text';
        break;
      case '--ghidra-dir':
        config.ghidra_install_dir = args[++i];
        break;
    }
  }

  const result = await runGhidraDisasm(config);
  console.log(JSON.stringify(result, null, 2));
}

main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
