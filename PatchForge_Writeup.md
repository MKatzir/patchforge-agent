# PatchForge: Automated Root-Cause Binary Patch Analysis

## Why This Matters: The WannaCry Case Study

In March 2017, Microsoft released security bulletin **MS17-010**, patching CVE-2017-0145 — the "EternalBlue" SMBv1 vulnerability. Two months later, in May 2017, the **WannaCry ransomware worm** weaponized this exploit and infected over **230,000 systems across 150 countries** in a single weekend. The UK's National Health Service was crippled: surgeries cancelled, ambulances diverted. The total damage exceeded **$4 billion**.

The patch existed. The fix was known. But organizations couldn't answer a simple question: *"What actually changed between the patched and unpatched code, and where else in our binaries does this same vulnerable pattern appear?"*

This is the gap PatchForge fills. When a new patch drops, security teams need to:
- Identify **exactly which functions changed**
- Understand **why** the change fixes the vulnerability
- Verify that the same vulnerable pattern doesn't exist elsewhere in their codebase

Doing this manually across thousands of binaries is impractical. PatchForge automates the entire pipeline.

---

## How to Use the Agent

```bash
# 1. Start the environment
docker compose up -d

# 2. Enter the agent workspace
docker compose exec agent-workspace bash

# 3. Place before/after binaries
cp /path/to/vuln_binary  binaries/old.bin
cp /path/to/patched_binary  binaries/new.bin

# 4. Run the agent
opencode

# 5. In OpenCode, invoke:
@manager use prompts/manager_init.txt \
  --unpatched /app/binaries/old.bin \
  --patched /app/binaries/new.bin \
  --output-dir /app/output
```

The agent autonomously:
1. **Global Analyzer** diffs the binaries via BinDiff, finding every changed function
2. **Local Analyzer** decompiles each changed function via Ghidra, writes analysis to chapter files
3. **Manager** synthesizes everything into `/app/output/writeup.md`

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  docker-compose.yml                                     │
│                                                         │
│  ┌─ agent-workspace ──────────────────────────────────┐ │
│  │  OpenCode CLI  ─── @manager agent .md              │ │
│  │    │                                                │ │
│  │    │  task @global-analyzer                         │ │
│  │    │    │  bash: npx tsx /app/tools/bindiff.ts     │ │
│  │    │    │  task @local-analyzer <address>           │ │
│  │    │    │    bash: npx tsx /app/tools/ghidra_*.ts  │ │
│  │    │    │    bash: python3 /app/harness/write_*     │ │
│  │    │                                                │ │
│  │    │  HTTP POST http://tools:8000                   │ │
│  │    │    ▼                                           │ │
│  │  ┌──────────────────┐     ┌──────────────────┐     │ │
│  │  │ TS Wrappers      │────►│ FastAPI          │     │ │
│  │  │ (path translate,  │     │ job_server.py    │     │ │
│  │  │  /app/ → /work/)  │◄────│ (cache, semaphore)│     │ │
│  │  └──────────────────┘     └────────┬─────────┘     │ │
│  └────────────────────────────────────┼───────────────┘ │
│                                       │                 │
│  ┌─ tools container ──────────────────┼───────────────┐ │
│  │  FastAPI spawns:                   │               │ │
│  │    ├─ /bindiff  ──► bindiff.py ──► BinDiff CLI    │ │
│  │    ├─ /disasm   ──► ghidra_disasm.py ──► Ghidra   │ │
│  │    ├─ /decompile──► ghidra_decompile.py──► Ghidra  │ │
│  │    ├─ /string   ──► string_analyzer.py──► strings  │ │
│  │    └─ /symbol   ──► symbol_analyzer.py──► nm/obj   │ │
│  │                                                     │ │
│  │  Ghidra 11.0.3 headless (semaphore=1)              │ │
│  │    └─ ghidra_scripts/                               │ │
│  │       ├─ disassemble.py (Jython)                    │ │
│  │       ├─ decompile.py   (Jython)                    │ │
│  │       └─ export_binexport.py (BinExport)            │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## Key Architecture Decisions

### 1. Two-Container Separation
The agent and analysis tools run in **separate Docker containers** communicating via HTTP. The agent never directly touches Ghidra, BinDiff, or system tools. This means a malicious binary (which you're analyzing, after all) cannot compromise the agent runtime — the worst it can do is crash a subprocess in the tools container. Different base images also allow independent rebuild cycles and scaling.

### 2. HTTP Bridge over Subprocess or Shared Volume
Each TypeScript wrapper translates paths (`/app/` → `/work/`) and POSTs JSON to the FastAPI backend. This gives clean **process isolation**, **network transparency** (you can `curl` any endpoint to debug), **statelessness**, and **consistent error handling** via the `ToolResult` interface. A shared volume would require both containers to agree on filesystem layout; subprocess calls would chain agent availability to tool availability.

### 3. SHA256 Caching + Filename Disambiguation
Every Ghidra decompile/disasm result is cached by `SHA256(binary)_filename_function_address`. The filename is included because test harnesses often create dummy binaries with identical content but different names — without it, caches would collide silently.

```python
def cache_key_for_function(binary_path, function_address, function_names):
    s = sha256_file(binary_path)
    base_name = os.path.basename(binary_path)
    return f"{base_name}_{s}_{function_address or function_names or 'all'}"
```

### 4. Ghidra Semaphore (MAX_GHIDRA=1)
Ghidra headless consumes 4–8 GB RAM per invocation. Running multiple instances simultaneously causes OOM kills. The `asyncio.Semaphore` serializes all Ghidra calls. This is acceptable because the LLM (agent thinking time) is the bottleneck, not Ghidra throughput.

```python
ghidra_sem = asyncio.Semaphore(MAX_GHIDRA)  # MAX_GHIDRA = 1

async with ghidra_sem:
    cmd = ["python3", "tools/ghidra/ghidra_decompile.py", ...]
    code, out, err = await run_subproc(cmd, timeout=req.timeout)
```

### 5. Error Responses Are Never Cached
If Ghidra crashes or a binary is malformed, the error response is written to stdout but **not** saved to the cache. This prevents a transient failure from blacklisting a function analysis permanently.

```python
# NEVER cache error responses
if "error" not in parsed and parsed.get("status") != "failed":
    with open(cache_file, "w") as f:
        json.dump(parsed, f)
```

### 6. Chapter System for Context Management
The Local Analyzer writes raw decompilation to numbered chapter files (`harness/db/chapter_{id}.json`) instead of returning megabytes of C code in the LLM response. The Global Analyzer reads these chapters on demand. This prevents LLM context overflow when analyzing large binaries with hundreds of functions.

### 7. Path Translation Middleware
The agent workspace mounts the project at `/app/`, but the tools container resolves binaries relative to `/work/`. Every TypeScript wrapper performs this translation before sending the request:

```typescript
const payload = {
  binary: config.binary.replace(/^\/app\//, '/work/'),
  // ...
};
```

### 8. BinExport Omni-Transplant (The Hardest Fix)
BinExport is the Ghidra plugin that exports binaries to the `.BinExport` format BinDiff requires. It's designed for the Ghidra GUI. Getting it to work headless required:
- **Unwrapping a nested zip** (the "Inception Zip Trap" — a zip inside a zip)
- **Replacing Ghidra's protobuf-java** (the "Protobuf Collision" — the bundled version conflicts with BinExport's required version)
- **Injecting jars into `/patch/`** to bypass Ghidra's GUI-enablement check

This fix is documented in `changelog.txt` and was the single most critical infrastructure challenge.

### 9. Smart Offset Fix
BinDiff returns addresses that may be **raw file offsets** rather than Ghidra's virtual addresses. Both Jython scripts (`disassemble.py`, `decompile.py`) automatically detect this and add the Image Base offset:

```python
# From ghidra_scripts/decompile.py (conceptual)
if function_address < currentProgram.getImageBase().getOffset():
    function_address += currentProgram.getImageBase().getOffset()
```

### 10. Non-Root User in Tools Container
The tools container runs as user `patch` (non-root), limiting the blast radius if a crafted binary exploits a Ghidra or Python vulnerability.

---

## Important Code Patterns

### The ToolResult Interface (all TS wrappers)
Every tool returns a standardized JSON envelope so the agent can parse results programmatically:

```typescript
{
  status: 'success' | 'error',
  tool_name: string,
  data: { ... },
  summary: string,
  metadata: { ai_next_step: string }
}
```

### Async Subprocess Runner (job_server.py)
All tool execution flows through a single `run_subproc` with timeout handling:

```python
async def run_subproc(cmd, timeout=300):
    proc = await asyncio.create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        raise HTTPException(status_code=504, detail="Tool timeout")
    return proc.returncode, stdout, stderr
```

### BinDiff SQLite Query (bindiff.py)
The core diffing logic queries the BinDiff SQLite database for functions with similarity below threshold:

```python
cursor.execute('''
    SELECT address1, address2, similarity, confidence, name2
    FROM function
    WHERE similarity < ? AND address2 IS NOT NULL
    ORDER BY similarity ASC
''', (self.threshold,))
```

Functions with **low similarity** are the ones that changed — these are the patch-relevant functions that get sent to the Local Analyzer for deep decompilation.

---

## Summary

PatchForge bridges the gap between **"a patch exists"** and **"we understand what the patch actually fixes."** By automating the four-step pipeline — diff, identify, decompile, explain — it turns a manual, days-long analysis into an autonomous process. The architecture prioritizes defense (separate containers, no exploit tooling), reproducibility (SHA256 caching, chapter system), and debuggability (HTTP endpoints, ToolResult envelope).

As WannaCry demonstrated, having the patch is not enough. You need to understand the root cause, find every vulnerable instance, and verify the fix. PatchForge makes that systematic.
