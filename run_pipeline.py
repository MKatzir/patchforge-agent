import os
import sys
import subprocess

# Define the paths mapping templates to their decoupled prompts
AGENT_CONFIGS = {
    "manager": {
        "template": "/app/.opencode/agents/manager.template.md",
        "prompt": "/app/prompts/sys_manager.txt",
        "output": "/app/.opencode/agents/manager.md"
    },
    "global-analyzer": {
        "template": "/app/.opencode/agents/global-analyzer.template.md",
        "prompt": "/app/prompts/sys_global_analyzer.txt",
        "output": "/app/.opencode/agents/global-analyzer.md"
    },
    "local-analyzer": {
        "template": "/app/.opencode/agents/local-analyzer.template.md",
        "prompt": "/app/prompts/sys_local_analyzer.txt",
        "output": "/app/.opencode/agents/local-analyzer.md"
    },
    "test-writer": {
        "template": "/app/.opencode/agents/test-writer.template.md",
        "prompt": "/app/prompts/sys_test_writer.txt",
        "output": "/app/.opencode/agents/test-writer.md"
    }
}

def compile_agent_profiles():
    """Injects decoupled text prompts into the OpenCode agent markdown templates."""
    print("[*] Bootstrapping Agent Configurations...")
    
    for agent, paths in AGENT_CONFIGS.items():
        try:
            # 1. Read the template
            with open(paths["template"], "r", encoding="utf-8") as tpl_file:
                template_content = tpl_file.read()
            
            # 2. Read the prompt
            with open(paths["prompt"], "r", encoding="utf-8") as prompt_file:
                prompt_content = prompt_file.read()
            
            # 3. Inject and compile
            compiled_content = template_content.replace("{{SYSTEM_PROMPT}}", prompt_content)
            
            # 4. Write the final output for OpenCode to consume
            with open(paths["output"], "w", encoding="utf-8") as out_file:
                out_file.write(compiled_content)
                
            print(f"    [+] Successfully compiled {paths['output']}")
            
        except FileNotFoundError as e:
            print(f"    [!] Error building {agent}: {e}")
            sys.exit(1)

def main():
    # 1. Pre-flight: Build the agent files dynamically
    compile_agent_profiles()
    
    # 2. Your existing setup code...
    # e.g., load manager_init.txt and pass it to OpenCode
    print("[*] Starting PatchForge Pipeline...")
    # subprocess.run(["opencode", "start", "--agent", "manager"], check=True)

if __name__ == "__main__":
    main()
