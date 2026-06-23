#!/usr/bin/env python3
import os
import hashlib
import json
import subprocess
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Patch Tools API")

WORK_DIR = os.environ.get("WORK_DIR", "/work")
GHIDRA_INSTALL_DIR = os.environ.get("GHIDRA_INSTALL_DIR", "/app/ghidra_install")
CACHE_DIR = os.path.join(WORK_DIR, "cache")
OUTPUT_DIR = os.path.join(WORK_DIR, "output")
MAX_GHIDRA = int(os.environ.get("MAX_GHIDRA_JOBS", "1"))

ghidra_sem = asyncio.Semaphore(MAX_GHIDRA)

# Helper models
class BinPair(BaseModel):
    before: str
    after: str
    similarity_threshold: Optional[float] = 0.95
    min_block_size: Optional[int] = 10
    opcode_only: Optional[bool] = False

class FuncRequest(BaseModel):
    binary: str
    function_address: Optional[str] = None
    function_names: Optional[str] = None  # comma separated
    timeout: Optional[int] = 300
    ignore_cache: Optional[bool] = False  # Allows bypassing the cache completely

class StringAnalyzerRequest(BaseModel):
    binary: str
    min_length: Optional[int] = 4
    encoding: Optional[str] = "ascii"  # all, ascii, unicode, utf16
    search_pattern: Optional[str] = None

class SymbolAnalyzerRequest(BaseModel):
    binary: str
    symbol_types: Optional[str] = None
    demangle: Optional[bool] = False

# Helpers
def abs_path(p: str) -> str:
    if os.path.isabs(p):
        return p
    return os.path.normpath(os.path.join(WORK_DIR, p))

def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

async def run_subproc(cmd, timeout=300):
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise HTTPException(status_code=504, detail="Tool timeout")
        return proc.returncode, stdout.decode("utf-8", errors="ignore"), stderr.decode("utf-8", errors="ignore")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints
@app.get("/health")
async def health():
    return {"status": "ok", "ghidra": os.path.exists(os.path.join(GHIDRA_INSTALL_DIR, "support", "analyzeHeadless"))}

@app.post("/bindiff")
async def bindiff(pair: BinPair):
    before = abs_path(pair.before)
    after = abs_path(pair.after)
    if not os.path.exists(before) or not os.path.exists(after):
        raise HTTPException(status_code=404, detail="before/after binary not found")
    cmd = ["python3", "tools/bindiff/bindiff.py", "--before", before, "--after", after, 
           "--similarity-threshold", str(pair.similarity_threshold),
           "--min-block-size", str(pair.min_block_size)]
    if pair.opcode_only:
        cmd.append("--opcode-only")
    code, out, err = await run_subproc(cmd, timeout=120)
    if code != 0:
        raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}

def cache_key_for_function(binary_path: str, function_address: Optional[str], function_names: Optional[str]) -> str:
    s = sha256_file(binary_path)
    base_name = os.path.basename(binary_path)
    # Include the filename so dummy files and real files with matching hashes never collide
    return f"{base_name}_{s}_{function_address or function_names or 'all'}"

@app.post("/disasm")
async def disasm(req: FuncRequest):
    binary = abs_path(req.binary)
    if not os.path.exists(binary):
        raise HTTPException(status_code=404, detail="binary not found")
    
    key = cache_key_for_function(binary, req.function_address, req.function_names)
    cache_file = os.path.join(CACHE_DIR, f"disasm_{key}.json")
    
    if not req.ignore_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    async with ghidra_sem:
        cmd = ["python3", "tools/ghidra/ghidra_disasm.py", "--binary", binary, "--ghidra-dir", GHIDRA_INSTALL_DIR, "--output-format", "json"]
        if req.function_address:
            cmd.extend(["--function-address", req.function_address])
        if req.function_names:
            cmd.extend(["--function-names", req.function_names])
        
        code, out, err = await run_subproc(cmd, timeout=req.timeout)
        if code != 0:
            raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
            
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            parsed = {"raw": out}
            
        # NEVER cache error responses
        if "error" not in parsed and parsed.get("status") != "failed":
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(parsed, f)
                
        return parsed

@app.post("/decompile")
async def decompile(req: FuncRequest):
    binary = abs_path(req.binary)
    if not os.path.exists(binary):
        raise HTTPException(status_code=404, detail="binary not found")
        
    key = cache_key_for_function(binary, req.function_address, req.function_names)
    cache_file = os.path.join(CACHE_DIR, f"decomp_{key}.json")
    
    if not req.ignore_cache and os.path.exists(cache_file):
        with open(cache_file, "r") as f:
            return json.load(f)

    async with ghidra_sem:
        cmd = ["python3", "tools/ghidra/ghidra_decompile.py", "--binary", binary, "--ghidra-dir", GHIDRA_INSTALL_DIR, "--output-format", "json"]
        if req.function_address:
            cmd.extend(["--function-address", req.function_address])
        if req.function_names:
            cmd.extend(["--function-names", req.function_names])
            
        code, out, err = await run_subproc(cmd, timeout=req.timeout)
        if code != 0:
            raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
            
        try:
            parsed = json.loads(out)
        except json.JSONDecodeError:
            parsed = {"raw": out}
            
        # NEVER cache error responses
        if "error" not in parsed and parsed.get("status") != "failed":
            os.makedirs(CACHE_DIR, exist_ok=True)
            with open(cache_file, "w") as f:
                json.dump(parsed, f)
                
        return parsed

@app.post("/string_analyzer")
async def string_analyzer(req: StringAnalyzerRequest):
    binary = abs_path(req.binary)
    if not os.path.exists(binary):
        raise HTTPException(status_code=404, detail="binary not found")
    
    cmd = ["python3", "tools/analysis/string_analyzer.py", "--binary", binary, "--output-format", "json"]
    if req.min_length:
        cmd.extend(["--min-length", str(req.min_length)])
    if req.encoding:
        cmd.extend(["--encoding", req.encoding])
    if req.search_pattern:
        cmd.extend(["--search-pattern", req.search_pattern])
    
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
    
    cmd = ["python3", "tools/analysis/symbol_analyzer.py", "--binary", binary, "--output-format", "json"]
    if req.symbol_types:
        cmd.extend(["--symbol-types", req.symbol_types])
    if req.demangle:
        cmd.append("--demangle")
    
    code, out, err = await run_subproc(cmd, timeout=60)
    if code != 0:
        raise HTTPException(status_code=500, detail={"error": err, "stdout": out})
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return {"raw": out}

@app.get("/cache/{kind}/{key}")
async def get_cache(kind: str, key: str):
    path = os.path.join(CACHE_DIR, f"{kind}_{key}.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="cache not found")
    with open(path, "r") as f:
        return json.load(f)