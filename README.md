# PatchForge: Vulnerability Research & PoC Generation System

PatchForge is an automated vulnerability research platform that performs binary diffing, root-cause analysis, and proof-of-concept exploit generation. It uses a swarm of specialized AI agents coordinated through OpenCode to analyze security patches and generate educational PoC exploits.

## Features

🔍 **Binary Diffing** - Structural comparison of patched vs unpatched binaries using BinDiff  
🔎 **Deep Analysis** - Semantic extraction of vulnerable functions using Ghidra  
📝 **Writeup Generation** - Automated root-cause analysis reports  
💣 **PoC Generation** - Educational proof-of-concept exploits (C/Python)  
📖 **Documentation** - Complete exploitation guides with setup instructions  
🤖 **Multi-Agent System** - Coordinated AI agents for complex analysis workflows  

## Quick Start

### Prerequisites
- Docker & Docker Compose
- OpenCode CLI installed
- Binary analysis tools (Ghidra, BinDiff) - included in Docker image

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd patch-agent-lab

# Validate agent setup
python3 run_pipeline.py

# Start the analysis pipeline
opencode
```

### Running an Analysis

```bash
# In OpenCode, invoke the manager agent
@manager "Analyze the security patch in /app/binaries/"
```

The pipeline will:
1. **Global Analyzer** - Performs binary diffing to identify changes
2. **Local Analyzer** - Deep-dives into changed functions  
3. **PoC Builder** - Generates exploit code and documentation

Results are saved to `/app/output/`:
- `writeup.md` - Comprehensive vulnerability analysis
- `poc.c` or `poc.py` - Proof-of-concept exploit code
- `poc_explanation.md` - Detailed exploitation guide

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│              PATCHFORGE ANALYSIS SYSTEM                 │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  MANAGER AGENT                                           │
│  └─ Orchestrates the full pipeline                      │
│     ├─→ GLOBAL ANALYZER                                │
│     │   └─ BinDiff & vulnerability discovery            │
│     │   └─→ LOCAL ANALYZER                             │
│     │       └─ Function-level analysis via Ghidra      │
│     │                                                   │
│     └─→ POC BUILDER                                    │
│         └─ Generates exploits & documentation          │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### The 4 Agents

| Agent | Role | Output |
|-------|------|--------|
| **Manager** | Orchestrates analysis workflow | Coordination logs |
| **Global Analyzer** | Binary diffing & patch analysis | writeup.md |
| **Local Analyzer** | Deep function extraction | Chapter_*.md (database) |
| **PoC Builder** | Exploit generation | poc.c/py + poc_explanation.md |

## Project Structure

```
patch-agent-lab/
├── .opencode/
│   └── agents/              # Agent definitions
│       ├── manager.md
│       ├── global-analyzer.md
│       ├── local-analyzer.md
│       └── poc-builder.md (NEW)
│
├── tools/                   # Binary analysis tools
│   ├── bindiff/
│   ├── ghidra/
│   └── analysis/
│
├── binaries/                # Input binaries (old.bin, new.bin)
├── output/                  # Analysis results
├── cache/                   # Cached analysis data
├── harness/                 # Database & test utilities
│
├── docker-compose.yml       # Service configuration
├── Dockerfile              # Agent container
├── Dockerfile.tools        # Tools container (Ghidra, BinDiff)
│
└── run_pipeline.py          # Agent validation script
```

## Usage Examples

### Basic Analysis

```bash
# Start the system
docker-compose up -d

# Enter OpenCode
opencode

# Analyze binaries
@manager "Compare /app/binaries/old.bin against /app/binaries/new.bin"
```

### Input Files

Place binary files in `/app/binaries/`:
- `old.bin` - Unpatched/vulnerable version
- `new.bin` - Patched/secure version

### Output

The analysis generates in `/app/output/`:

```markdown
# writeup.md
- Vulnerability summary
- Changed functions list
- Attack vectors identified
- Patch mechanism explained

# poc.c (or poc.py)
- Minimal exploit code
- Well-commented implementation
- Attack vector demonstration
- Patch prevention explanation

# poc_explanation.md
- Prerequisites for testing
- Compilation instructions
- Execution steps
- Expected vs patched behavior
- Security disclaimers
```

## Docker Deployment

### Services

**agent-workspace** - OpenCode agent execution environment
**tools** - FastAPI server for binary analysis tools

### Build & Run

```bash
# Build images
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f tools

# Stop services
docker-compose down
```

### Volume Mounts

- `./binaries/` → `/app/binaries/` - Input binaries
- `./output/` → `/app/output/` - Analysis results
- `./cache/` → `/work/cache/` - Analysis cache
- `./ghidra_projects/` → `/opt/ghidra/projects/` - Ghidra workspace

## Configuration

### Environment Variables

Set in `.env` file:
```
GHIDRA_INSTALL_DIR=/opt/ghidra
WORK_DIR=/work
MAX_GHIDRA_JOBS=1
```

### Tool Settings

Modify tool behavior in agent definitions (`.opencode/agents/*.md`):
- BinDiff: Similarity thresholds, block sizes, opcode-only mode
- Ghidra: Timeout, function addresses, decompilation depth

## Documentation

### For Quick Start
→ Read [QUICKSTART_POC_BUILDER.md](QUICKSTART_POC_BUILDER.md)

### For Complete Technical Guide
→ Read [POC_BUILDER_INTEGRATION.md](POC_BUILDER_INTEGRATION.md)

### For Architecture Overview
→ Read [AGENT_SYSTEM_REFERENCE.md](AGENT_SYSTEM_REFERENCE.md)

### For Implementation Details
→ Read [POC_BUILDER_IMPLEMENTATION.md](POC_BUILDER_IMPLEMENTATION.md)

## Key Technologies

- **OpenCode** - Multi-agent AI orchestration
- **Ghidra** - Decompilation & disassembly
- **BinDiff** - Binary structural comparison
- **FastAPI** - Tool backend server
- **TypeScript/Python** - Tool wrappers
- **Docker** - Containerized deployment

## Workflow Timeline

| Phase | Duration | Generates |
|-------|----------|-----------|
| Global Analyzer | 5-10 min | writeup.md |
| Local Analyzer | Variable | Chapter_*.md |
| PoC Builder | 5-15 min | poc.c + poc_explanation.md |
| **Total** | **10-25 min** | **Complete analysis** |

## Security & Ethics

⚠️ **Educational Use Only** - PoC code is for learning vulnerability mechanics

⚠️ **Authorized Testing Only** - Only use on systems you own or have permission to test

✓ **Defensive Research** - Designed for understanding security patches

✓ **No Remote Exploitation** - All tools are local, source-code focused

✓ **Security Disclaimers** - All generated code includes appropriate warnings

## Development

### Adding Tools

New binary analysis tools go in `tools/` subdirectories:
```
tools/
├── bindiff/           # Binary diffing
├── ghidra/            # Decompilation/disassembly
└── analysis/          # String/symbol analysis
```

Tools should have both Python (backend) and TypeScript (frontend) implementations.

### Extending Agents

Agent definitions in `.opencode/agents/*.md` can be modified to:
- Change analysis parameters
- Add new tool invocations
- Extend output documentation
- Modify task delegation

### Custom Output

Agents write results to:
- `/app/output/` - Final deliverables (writeup.md, poc.c, etc.)
- `/app/harness/db/` - Function analysis database
- `/app/cache/` - Cached analysis results

## Troubleshooting

### Agent Validation
```bash
python3 run_pipeline.py
```
Should show all 4 agents validated.

### Missing Outputs
- Verify Global Analyzer completed (check `writeup.md` exists)
- Check Manager invoked PoC Builder (review logs)
- Ensure `/app/output/` directory is writable

### Docker Issues
```bash
# Rebuild images
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Tool Errors
Check tool logs in Docker container:
```bash
docker-compose logs tools
```

## Performance

- **CPU**: Moderate (mostly I/O bound during Ghidra analysis)
- **Memory**: 2-4 GB recommended
- **Disk**: 1-2 GB for analysis cache
- **Network**: Not required (offline capable)

## Version Info

- **System**: PatchForge 2.0
- **Agents**: 4 (Manager, Global Analyzer, Local Analyzer, PoC Builder)
- **OpenCode**: 1.17.7+
- **Status**: Production Ready ✅

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

For issues or questions:
1. Check troubleshooting in documentation
2. Review agent logs in Docker
3. Run `python3 run_pipeline.py` to validate setup
4. See detailed guides in documentation folder

## References

- [Ghidra Documentation](https://ghidra-sre.org/)
- [BinDiff Documentation](https://www.zynamics.com/bindiff.html)
- [OpenCode Documentation](https://opencode.ai/)

---

**Quick Links**
- 📖 [QUICKSTART_POC_BUILDER.md](QUICKSTART_POC_BUILDER.md) - 5-minute guide
- 🏗️ [AGENT_SYSTEM_REFERENCE.md](AGENT_SYSTEM_REFERENCE.md) - Architecture
- 📋 [POC_BUILDER_INDEX.md](POC_BUILDER_INDEX.md) - Documentation index

**Status**: ✅ Ready to use | Last Updated: 2024-06-23
