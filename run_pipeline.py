#!/usr/bin/env python3
"""
PatchForge Agent Bootstrapper.

Validates that all required agent files exist. The agent markdown files
(.opencode/agents/*.md) are maintained directly and do not require
template injection.

Usage: python3 run_pipeline.py
"""

import os
import sys

AGENT_FILES = {
    "manager": "/app/.opencode/agents/manager.md",
    "global-analyzer": "/app/.opencode/agents/global-analyzer.md",
    "local-analyzer": "/app/.opencode/agents/local-analyzer.md",
    "poc-builder": "/app/.opencode/agents/poc-builder.md",
}

def validate_agents():
    print("[*] Validating agent configurations...")
    all_ok = True
    for agent, path in AGENT_FILES.items():
        if os.path.exists(path):
            size = os.path.getsize(path)
            print(f"    [+] {agent}: {path} ({size} bytes)")
        else:
            print(f"    [!] {agent}: {path} NOT FOUND")
            all_ok = False
    return all_ok

def main():
    if not validate_agents():
        print("[!] One or more agent files missing. Cannot proceed.")
        sys.exit(1)

    print("[*] All agent files validated successfully.")
    print("[*] To start the pipeline, run: opencode")
    print("[*] Use @manager agent to begin a new analysis.")

if __name__ == "__main__":
    main()