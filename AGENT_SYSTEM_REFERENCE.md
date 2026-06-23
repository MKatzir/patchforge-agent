# PatchForge Agent System - Quick Reference

## Agent Hierarchy

```
PatchForge Analysis Pipeline
═══════════════════════════════════════════════════════════════════

                           ┌──────────────┐
                           │   Manager    │
                           │  (Conductor) │
                           └──────┬───────┘
                                  │
                   ┌──────────────┴──────────────┐
                   │                             │
        ┌──────────▼─────────────┐   ┌──────────▼──────────────┐
        │   Global Analyzer     │   │    PoC Builder         │
        │  (Binary Diffing)      │   │ (Exploit Generation)   │
        └──────────┬──────────────┘   └─────────┬──────────────┘
                   │                            │
        ┌──────────▼─────────────┐              │
        │   Local Analyzer      │              │
        │ (Deep Static Analysis)│              │
        └────────────────────────┘              │
                   │                            │
        ┌──────────▼─────────────────────────────▼─────────────┐
        │              Output Generation                        │
        ├────────────────────────────────────────────────────┤
        │  writeup.md            │ poc.c / poc.py             │
        │  (Vulnerability Facts) │ (Proof of Concept)         │
        │                        │                            │
        │  Chapter_*.md          │ poc_explanation.md         │
        │  (Function Analysis)   │ (Exploitation Guide)       │
        └────────────────────────────────────────────────────┘
```

## Agent Details

### 1. Manager Agent
```
Status: ORCHESTRATOR
Type: Coordinator
Role: Pipeline control and delegation

Workflow:
  1. Receive binary paths
  2. Delegate to Global Analyzer
  3. Wait for writeup.md
  4. Delegate to PoC Builder
  5. Provide final summary

Tools Available:
  - task (for delegation)
  - bash (for verification)
```

### 2. Global Analyzer Agent
```
Status: DISCOVERY
Type: Binary Analysis
Role: Patch vulnerability identification

Input:
  - /app/binaries/old.bin (unpatched)
  - /app/binaries/new.bin (patched)

Process:
  1. BinDiff structural comparison
  2. Function-level diffing
  3. Delegate to Local Analyzer
  4. Synthesize findings

Output:
  - /app/output/writeup.md

Tools Available:
  - bash (for tool execution)
  - task (for delegation)
```

### 3. Local Analyzer Agent
```
Status: DEEP ANALYSIS
Type: Function-level Analysis
Role: Semantic code extraction

Input:
  - Binary path
  - Function address
  - Optional: function names

Process:
  1. Decompile at address (Ghidra)
  2. Disassemble at address (Ghidra)
  3. Extract vulnerability mechanics
  4. Document in database

Output:
  - /app/harness/db/Chapter_*.md

Tools Available:
  - bash (for tool execution)
  - Cannot: apt-get, wget, curl, npm install, radare2
```

### 4. PoC Builder Agent (NEW)
```
Status: PROOF-OF-CONCEPT
Type: Exploit Development
Role: Vulnerability demonstration

Input:
  - /app/output/writeup.md (from Global Analyzer)

Process:
  1. Analyze vulnerability findings
  2. Identify attack vector
  3. Generate minimal PoC code
  4. Create exploitation guide
  5. Verify code quality

Output:
  - /app/output/poc.c or poc.py
  - /app/output/poc_explanation.md

Tools Available:
  - bash (for syntax verification)
  - file operations (for writing code)

Constraints:
  - Educational purpose only
  - No external dependencies
  - Self-contained code
  - Source generation only
```

## Communication Flow

### Agent-to-Agent Communication

```
Manager → Global Analyzer:
  task global-analyzer "Perform patch diffing on --before /app/binaries/old.bin 
                        --after /app/binaries/new.bin"
  
    ↓
    
Global Analyzer → Local Analyzer:
  task local-analyzer "Analyze changed function at --function-address 0x9270 
                       in /app/binaries/new.bin"
  
    ↓
    
Local Analyzer → (returns to Global Analyzer)
  Returns 2-3 sentence summary of findings
  
    ↓
    
Global Analyzer → (returns to Manager)
  Completes analysis, writeup.md created
  
    ↓
    
Manager → PoC Builder:
  task poc-builder "Create a proof-of-concept exploit based on the 
                   vulnerability analysis in /app/output/writeup.md"
  
    ↓
    
PoC Builder → (returns to Manager)
  Completes PoC generation, poc.c and poc_explanation.md created
```

## Input/Output Data Flow

```
                    ┌─────────────────────┐
                    │   User Provides     │
                    │  - old.bin path     │
                    │  - new.bin path     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  Global Analyzer    │
                    │  BinDiff Analysis   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │ writeup.md Created  │
                    │ - Vulnerability ID  │
                    │ - Attack vectors    │
                    │ - Patch details     │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  PoC Builder        │
                    │  Exploit Gen        │
                    └──────────┬──────────┘
                               │
           ┌───────────────────┼───────────────────┐
           │                   │                   │
    ┌──────▼──────┐   ┌────────▼────────┐  ┌──────▼──────────┐
    │  poc.c/py   │   │ poc_explanation │  │  Verification   │
    │  Exploit    │   │  Guide & Docs   │  │  Report         │
    │  Code       │   │                 │  │                 │
    └─────────────┘   └─────────────────┘  └─────────────────┘
```

## File Organization

### Agent Configuration Files
```
.opencode/agents/
├── manager.md ..................... Manager/Orchestrator
├── global-analyzer.md ............. Binary Diffing
├── local-analyzer.md .............. Function Analysis
└── poc-builder.md ................. PoC Generation [NEW]
```

### Initialization & Control
```
prompts/
└── manager_init.txt ............... Manager initialization [UPDATED]

run_pipeline.py .................... Agent validation [UPDATED]
```

### Output & Analysis Data
```
output/
├── writeup.md ..................... Vulnerability analysis
├── poc.c or poc.py ................ PoC code [NEW]
├── poc_explanation.md ............. PoC guide [NEW]
└── .gitkeep

harness/db/
└── Chapter_*.md ................... Function analysis details
```

## Execution Timeline

### Complete Analysis Run

```
T+0s   │ Manager starts
       │ ├─ Initialize pipeline
       │ └─ Delegate to Global Analyzer
       │
T+5s   │ Global Analyzer running
       │ ├─ Execute BinDiff
       │ ├─ Analyze results
       │ └─ Delegate to Local Analyzer
       │
T+30s  │ Local Analyzer working
       │ ├─ Extract function code
       │ ├─ Analyze semantics
       │ └─ Return findings
       │
T+45s  │ Global Analyzer completing
       │ ├─ Synthesize findings
       │ ├─ Write writeup.md
       │ └─ Return to Manager
       │
T+50s  │ Manager receives results
       │ ├─ Verify writeup.md
       │ └─ Delegate to PoC Builder
       │
T+55s  │ PoC Builder working
       │ ├─ Read writeup.md
       │ ├─ Generate PoC code
       │ ├─ Generate documentation
       │ └─ Return to Manager
       │
T+70s  │ Manager receiving results
       │ ├─ Verify outputs
       │ └─ Provide final summary
       │
T+75s  │ COMPLETE
       │ ├─ writeup.md ✓
       │ ├─ poc.c ✓
       │ └─ poc_explanation.md ✓
```

## Quick Start

### 1. Validate Agents
```bash
python3 run_pipeline.py
# Expected: All 4 agents validated ✓
```

### 2. Start Pipeline
```bash
opencode
```

### 3. Invoke Manager
```
@manager "Analyze vulnerability in /app/binaries/old.bin vs /app/binaries/new.bin"
```

### 4. Wait for Completion
- Monitor `/app/output/` for files
- Global Analyzer → writeup.md (5-10 min)
- PoC Builder → poc.c + poc_explanation.md (5-15 min)

### 5. Review Results
```bash
# Vulnerability analysis
cat /app/output/writeup.md

# Proof of concept
cat /app/output/poc.c
cat /app/output/poc_explanation.md

# Function details
ls /app/harness/db/Chapter_*.md
```

## Agent Capabilities Matrix

| Capability | Manager | Global | Local | PoC Builder |
|-----------|---------|--------|-------|-------------|
| Binary diffing | - | ✓ | - | - |
| Function analysis | - | - | ✓ | - |
| Writeup generation | ✓ | ✓ | - | - |
| PoC generation | - | - | - | ✓ |
| Code extraction | - | - | ✓ | - |
| Orchestration | ✓ | - | - | - |
| Delegation | ✓ | ✓ | - | - |
| Documentation | ✓ | ✓ | ✓ | ✓ |

## Status: ✓ ACTIVE

All 4 agents operational and integrated:
- ✓ Manager (Orchestrator)
- ✓ Global Analyzer (Binary Diffing)
- ✓ Local Analyzer (Function Analysis)
- ✓ PoC Builder (Exploit Generation) [NEW]
