#!/usr/bin/env node

/**
 * String Analyzer Tool - TypeScript Wrapper (Refactored for OpenCode)
 * Extracts and analyzes strings from binaries via FastAPI server.
 */

interface StringAnalyzerConfig {
  binary_path: string;
  min_length?: number;
  encoding?: 'all' | 'ascii' | 'unicode' | 'utf16';
  search_pattern?: string;
}

interface ToolResult {
  status: 'success' | 'error';
  tool_name: string;
  execution_time_ms: number;
  data: any;
  summary: string;
  metadata: { ai_next_step?: string; [key: string]: any };
}

async function runStringAnalyzer(config: StringAnalyzerConfig): Promise<ToolResult> {
  const startTime = Date.now();

  try {
    if (!config.binary_path) {
      throw new Error('binary_path is required');
    }

    const payload: Record<string, any> = { binary: config.binary_path };
    if (config.min_length !== undefined) payload.min_length = config.min_length;
    if (config.encoding) payload.encoding = config.encoding;
    if (config.search_pattern) payload.search_pattern = config.search_pattern;

    const apiUrl = 'http://tools:8000/string_analyzer';
    let response;
    try {
      response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: AbortSignal.timeout(60000)
      });
    } catch (fetchError) {
      const errorMsg = fetchError instanceof Error ? fetchError.message : String(fetchError);
      return {
        status: 'error', tool_name: 'string_analyzer',
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
        status: 'error', tool_name: 'string_analyzer',
        execution_time_ms: Date.now() - startTime,
        data: { error: `HTTP ${response.status}`, details: errorDetail },
        summary: `FastAPI server returned error: ${response.status} - ${errorDetail}`,
        metadata: { ai_next_step: 'Verify binary file exists and is readable on tools container' }
      };
    }

    let responseData;
    try {
      responseData = await response.json();
    } catch {
      const rawText = await response.text();
      return {
        status: 'error', tool_name: 'string_analyzer',
        execution_time_ms: Date.now() - startTime,
        data: { raw: rawText },
        summary: 'Failed to parse FastAPI response as JSON',
        metadata: { ai_next_step: 'Check server logs for string extraction errors' }
      };
    }

    return {
      status: 'success',
      tool_name: 'string_analyzer',
      execution_time_ms: Date.now() - startTime,
      data: responseData,
      summary: `Successfully extracted strings from ${config.binary_path} (${responseData.count || '?'} strings found)`,
      metadata: {
        ai_next_step: 'Review strings for security-relevant content (error messages, URLs, version info, credentials)'
      }
    };
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      status: 'error', tool_name: 'string_analyzer',
      execution_time_ms: Date.now() - startTime,
      data: { error: message },
      summary: `String analyzer error: ${message}`,
      metadata: { ai_next_step: 'Check configuration and ensure binary file is valid' }
    };
  }
}

async function main() {
  const args = process.argv.slice(2);
  const config: StringAnalyzerConfig = { binary_path: '' };

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--binary': config.binary_path = args[++i]; break;
      case '--min-length': config.min_length = parseInt(args[++i], 10); break;
      case '--encoding': config.encoding = args[++i] as StringAnalyzerConfig['encoding']; break;
      case '--search-pattern': config.search_pattern = args[++i]; break;
    }
  }

  const result = await runStringAnalyzer(config);
  console.log(JSON.stringify(result, null, 2));
}

if (require.main === module) {
  main().catch((err) => {
    console.error(JSON.stringify({
      status: 'error', tool_name: 'string_analyzer', execution_time_ms: 0,
      data: { error: err.message },
      summary: `Fatal error: ${err.message}`,
      metadata: { ai_next_step: 'Check logs' }
    }, null, 2));
    process.exit(1);
  });
}

export { runStringAnalyzer, StringAnalyzerConfig, ToolResult };