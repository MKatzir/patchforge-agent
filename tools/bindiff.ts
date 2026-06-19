#!/usr/bin/env node

/**
 * BinDiff Tool - TypeScript Wrapper (Refactored for OpenCode)
 * Compares two binary files and identifies changed functions via FastAPI server.
 *
 * This wrapper communicates with the FastAPI job server (http://tools:8000) instead
 * of spawning child processes. It sends HTTP requests and parses responses.
 */

interface BinDiffConfig {
  before_binary: string;
  after_binary: string;
  similarity_threshold?: number;
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

async function runBinDiff(config: BinDiffConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    if (!config.before_binary || !config.after_binary) {
      throw new Error('before_binary and after_binary paths are required');
    }

    const payload: Record<string, any> = {
      before: config.before_binary,
      after: config.after_binary,
      similarity_threshold: config.similarity_threshold || 0.7
    };

    const apiUrl = 'http://tools:8000/bindiff';
    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(120000)
      });
    } catch (fetchError) {
      const errorMsg = fetchError instanceof Error ? fetchError.message : String(fetchError);
      return {
        status: 'error',
        tool_name: 'bindiff',
        execution_time_ms: Date.now() - startTime,
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
      return {
        status: 'error',
        tool_name: 'bindiff',
        execution_time_ms: Date.now() - startTime,
        data: { error: `HTTP ${response.status}`, details: errorDetail },
        summary: `FastAPI server returned error: ${response.status} - ${errorDetail}`,
        metadata: {
          ai_next_step: 'Verify binary files exist and are readable on tools container'
        }
      };
    }

    let responseData;
    try {
      responseData = await response.json();
    } catch {
      const rawText = await response.text();
      return {
        status: 'error',
        tool_name: 'bindiff',
        execution_time_ms: Date.now() - startTime,
        data: { raw: rawText },
        summary: 'Failed to parse FastAPI response as JSON',
        metadata: {
          ai_next_step: 'Check server logs for BinDiff execution errors'
        }
      };
    }

    return {
      status: 'success',
      tool_name: 'bindiff',
      execution_time_ms: Date.now() - startTime,
      data: responseData,
      summary: `Successfully compared ${config.before_binary} and ${config.after_binary} (threshold: ${config.similarity_threshold || 0.7})`,
      metadata: {
        ai_next_step: 'Review matched/unmatched functions; identify functions that changed'
      }
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      status: 'error',
      tool_name: 'bindiff',
      execution_time_ms: Date.now() - startTime,
      data: { error: message },
      summary: `BinDiff error: ${message}`,
      metadata: {
        ai_next_step: 'Check configuration and ensure binary files are valid'
      }
    };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: BinDiffConfig = {
    before_binary: '',
    after_binary: ''
  };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--before': config.before_binary = args[++i]; break;
      case '--after': config.after_binary = args[++i]; break;
      case '--similarity-threshold': config.similarity_threshold = parseFloat(args[++i]); break;
    }
  }

  const result = await runBinDiff(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(JSON.stringify({
      status: 'error', tool_name: 'bindiff', execution_time_ms: 0,
      data: { error: err.message },
      summary: `Fatal error: ${err.message}`,
      metadata: { ai_next_step: 'Check logs' }
    }, null, 2));
    process.exit(1);
  });
}

export { runBinDiff, BinDiffConfig, ToolResult };