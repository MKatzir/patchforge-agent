# TypeScript Tool Wrappers Refactoring Guide

## Overview

All five TypeScript tool wrappers in `tools/` have been refactored to use **HTTP requests** via `fetch` instead of spawning child processes. They now communicate with the FastAPI server running at `http://tools:8000` inside the `agent-workspace` Docker container.

## Refactored Files

1. **ghidra_decompile.ts** ✅ Uses POST `/decompile`
2. **ghidra_disasm.ts** ✅ Uses POST `/disasm`
3. **bindiff.ts** ✅ Uses POST `/bindiff`
4. **string_analyzer.ts** ✅ Uses POST `/string_analyzer` (NEW ENDPOINT NEEDED)
5. **symbol_analyzer.ts** ✅ Uses POST `/symbol_analyzer` (NEW ENDPOINT NEEDED)

## Key Changes

### All Files
- ❌ Removed: `import * as childProcess`
- ❌ Removed: `import * as fs` (no file existence checks on agent side)
- ❌ Removed: `import * as path`
- ✅ Added: Async HTTP `fetch` calls to `http://tools:8000/<endpoint>`
- ✅ Added: Graceful error handling for connection failures
- ✅ Added: JSON response parsing with fallback
- ✅ Added: Descriptive error messages for LLM agent readability

### Error Handling Pattern

All wrappers now:
1. **Catch connection errors** → Return `ToolResult` with `status: 'error'` and descriptive message
2. **Handle HTTP errors (4xx/5xx)** → Parse `response.detail` and return to LLM
3. **Handle JSON parse errors** → Return raw text in `data.raw`
4. **Never throw unhandled exceptions** → Always return a `ToolResult` object

This ensures the OpenCode LLM agent can read error text and understand what went wrong.

---

## Required FastAPI Endpoints

### 1. POST `/decompile` ✅ (Already Exists)

**Request Body:**
```json
{
  "binary": "/path/to/binary",
  "function_address": "0x1234" (optional),
  "function_names": "func1,func2" (optional, comma-separated),
  "timeout": 300 (optional, seconds)
}
```

**Response:**
```json
{
  "functions": [
    { "address": "0x1234", "name": "main", "decompiled": "void main() {...}" }
  ]
}
```

---

### 2. POST `/disasm` ✅ (Already Exists)

**Request Body:**
```json
{
  "binary": "/path/to/binary",
  "function_address": "0x1234" (optional),
  "function_names": "func1,func2" (optional, comma-separated),
  "timeout": 300 (optional, seconds)
}
```

**Response:**
```json
{
  "functions": [
    { "address": "0x1234", "name": "main", "disassembly": "push rbp\nmov rsp, rbp\n..." }
  ]
}
```

---

### 3. POST `/bindiff` ✅ (Already Exists)

**Request Body:**
```json
{
  "before": "/path/to/before_binary",
  "after": "/path/to/after_binary",
  "similarity_threshold": 0.7 (optional)
}
```

**Response:**
```json
{
  "matched": [
    { "before_addr": "0x1000", "before_name": "func1", "after_addr": "0x1050", "after_name": "func1", "similarity": 0.95 },
    { "before_addr": "0x2000", "before_name": "func2", "after_addr": "0x2100", "after_name": "func2", "similarity": 0.80 }
  ],
  "unmatched_before": [
    { "address": "0x3000", "name": "removed_func" }
  ],
  "unmatched_after": [
    { "address": "0x3100", "name": "new_func" }
  ]
}
```

---

### 4. POST `/string_analyzer` 🆕 (NEEDS IMPLEMENTATION)

**Request Body:**
```json
{
  "binary": "/path/to/binary",
  "min_length": 4 (optional, default 4),
  "encoding": "ascii" (optional: "all", "ascii", "unicode", "utf16"),
  "search_pattern": "https://" (optional, regex pattern)
}
```

**Response:**
```json
{
  "count": 245,
  "strings": [
    { "offset": "0x4050", "value": "https://example.com", "encoding": "ascii" },
    { "offset": "0x4100", "value": "Error: Failed to", "encoding": "ascii" },
    { "offset": "0x5000", "value": "v1.2.3", "encoding": "ascii" }
  ]
}
```

**Implementation Note:** Call existing `tools/string_analyzer.py` script, parse JSON output.

---

### 5. POST `/symbol_analyzer` 🆕 (NEEDS IMPLEMENTATION)

**Request Body:**
```json
{
  "binary": "/path/to/binary",
  "symbol_types": "T,t,U" (optional, nm symbol type codes),
  "demangle": true (optional)
}
```

**Response:**
```json
{
  "count": 89,
  "symbols": [
    { "address": "0x1000", "name": "main", "type": "T", "size": 256 },
    { "address": "0x2000", "name": "_ZN7MyClass4fooEi", "demangled": "MyClass::foo(int)", "type": "T", "size": 128 }
  ]
}
```

**Implementation Note:** Call existing `tools/symbol_analyzer.py` script, parse JSON output.

---

## Migration Steps

### Step 1: Verify Existing Endpoints

The three Ghidra-based and BinDiff endpoints already exist in `job_server.py`. No changes needed.

### Step 2: Add Missing Endpoints to `job_server.py`

Add these Pydantic models and endpoints:

```python
class StringAnalyzerRequest(BaseModel):
    binary: str
    min_length: Optional[int] = 4
    encoding: Optional[str] = "ascii"  # all, ascii, unicode, utf16
    search_pattern: Optional[str] = None

class SymbolAnalyzerRequest(BaseModel):
    binary: str
    symbol_types: Optional[str] = None
    demangle: Optional[bool] = False

@app.post("/string_analyzer")
async def string_analyzer(req: StringAnalyzerRequest):
    binary = abs_path(req.binary)
    if not os.path.exists(binary):
        raise HTTPException(status_code=404, detail="binary not found")
    
    cmd = ["python3", "tools/string_analyzer.py", "--binary", binary, "--output-format", "json"]
    if req.min_length: cmd.extend(["--min-length", str(req.min_length)])
    if req.encoding: cmd.extend(["--encoding", req.encoding])
    if req.search_pattern: cmd.extend(["--search-pattern", req.search_pattern])
    
    code, out, err = await run_subproc(cmd, timeout=60)
    if code != 0:
        raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}

@app.post("/symbol_analyzer")
async def symbol_analyzer(req: SymbolAnalyzerRequest):
    binary = abs_path(req.binary)
    if not os.path.exists(binary):
        raise HTTPException(status_code=404, detail="binary not found")
    
    cmd = ["python3", "tools/symbol_analyzer.py", "--binary", binary, "--output-format", "json"]
    if req.symbol_types: cmd.extend(["--symbol-types", req.symbol_types])
    if req.demangle: cmd.append("--demangle")
    
    code, out, err = await run_subproc(cmd, timeout=60)
    if code != 0:
        raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}
```

### Step 3: Test the Refactored Wrappers

From the `agent-workspace` container:

```bash
# Test bindiff (already working)
node tools/bindiff.ts --before /work/binaries/old.elf --after /work/binaries/new.elf

# Test ghidra_decompile (already working)
node tools/ghidra_decompile.ts --binary /work/binaries/app.elf

# Test ghidra_disasm (already working)
node tools/ghidra_disasm.ts --binary /work/binaries/app.elf --function-address 0x1000

# Test string_analyzer (requires new endpoint)
node tools/string_analyzer.ts --binary /work/binaries/app.elf

# Test symbol_analyzer (requires new endpoint)
node tools/symbol_analyzer.ts --binary /work/binaries/app.elf --demangle
```

---

## Response Format: `ToolResult` Structure

All wrappers return a consistent `ToolResult` object:

```typescript
interface ToolResult {
  status: 'success' | 'error';
  tool_name: string;
  execution_time_ms: number;
  data: any;                    // The actual tool output or error details
  summary: string;              // Human-readable one-liner for the LLM
  metadata: {
    ai_next_step?: string;      // Suggested next action for the LLM agent
    [key: string]: any;
  };
}
```

### Example Success Response

```json
{
  "status": "success",
  "tool_name": "bindiff",
  "execution_time_ms": 8420,
  "data": {
    "matched": [
      { "before_addr": "0x1000", "before_name": "main", "after_addr": "0x1050", "after_name": "main", "similarity": 0.95 }
    ],
    "unmatched_before": [],
    "unmatched_after": []
  },
  "summary": "Successfully compared /work/binaries/old.elf and /work/binaries/new.elf (threshold: 0.7)",
  "metadata": {
    "ai_next_step": "Review matched/unmatched functions; identify functions that changed"
  }
}
```

### Example Error Response

```json
{
  "status": "error",
  "tool_name": "ghidra_decompile",
  "execution_time_ms": 125,
  "data": {
    "error": "HTTP 500",
    "details": "binary not found"
  },
  "summary": "FastAPI server returned error: 500 - binary not found",
  "metadata": {
    "ai_next_step": "Check binary file format and Ghidra installation on tools container"
  }
}
```

---

## Benefits of HTTP-Based Architecture

| Aspect | Old (child_process) | New (HTTP/Fetch) |
|--------|-------------------|------------------|
| **Process Isolation** | Each tool spawn crashes agent | Failed request returns error to LLM |
| **Network Flexibility** | Must run on same machine | Can run on remote `tools` container |
| **Scalability** | Single instance | Can load-balance multiple tool servers |
| **Error Resilience** | Unhandled exceptions crash | Graceful error responses |
| **Debugging** | Stdio is hard to trace | HTTP logging in FastAPI |
| **Resource Usage** | Python interpreter per call | Python service pool |

---

## Known Limitations & TODOs

1. **File Validation Removed**: The `.ts` files no longer check if binary files exist locally (they're on the `tools` container). The FastAPI server validates this.

2. **Output Format Parameter Removed**: Old wrappers had `--output-format json|text`. Now always JSON via HTTP.

3. **Ghidra Install Dir**: Removed from TypeScript (set on FastAPI server via env var `GHIDRA_INSTALL_DIR`).

4. **Caching**: The FastAPI server handles caching for `/disasm` and `/decompile`. TypeScript wrappers don't need to implement cache logic.

5. **Timeout Handling**: `AbortSignal.timeout()` requires Node.js 17+. Ensure your `agent-workspace` container has Node.js 17 or later.

---

## Testing the Complete Flow

1. Start the `tools` FastAPI server: `docker-compose up tools`
2. Start the `agent-workspace` container: `docker-compose up agent-workspace`
3. Inside the container, run:
   ```bash
   node tools/ghidra_decompile.ts --binary /work/binaries/app.elf | jq .
   ```
4. Verify the response has `status: "success"` and parsed decompiled functions in `data`.

---

## Proof of Concept: ghidra_decompile.ts

The `ghidra_decompile.ts` file serves as a **reference implementation** for all other wrappers:

- ✅ Uses `fetch()` with JSON POST
- ✅ Sends request to `http://tools:8000/decompile`
- ✅ Handles connection errors gracefully
- ✅ Parses JSON responses
- ✅ Returns formatted `ToolResult` for LLM consumption
- ✅ Provides actionable `ai_next_step` metadata
- ✅ CLI interface for standalone testing

All other wrappers follow the same pattern with tool-specific endpoints and parameters.
