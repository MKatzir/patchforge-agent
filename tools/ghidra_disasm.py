#!/usr/bin/env python3

"""
Ghidra Disassembler Tool - Python Orchestrator
Runs Ghidra headless analyzer and Jython script to disassemble binaries
"""

import json
import sys
import os
import argparse
import tempfile
import subprocess
from pathlib import Path
from typing import Dict, List, Any

class GhidraDisassembler:
    def __init__(self, binary_path: str, ghidra_install_dir: str):
        self.binary_path = binary_path
        self.ghidra_install_dir = ghidra_install_dir
        self.jython_script = Path(__file__).parent / 'ghidra_scripts' / 'disassemble.py'

    def run_ghidra_analysis(self, output_file: str, function_filter: str = '') -> Dict[str, Any]:
        """
        Run Ghidra's headless analyzer with Jython script
        """
        try:
            analyze_sh = Path(self.ghidra_install_dir) / 'support' / 'analyzeHeadless'
            
            if not analyze_sh.exists():
                # Try alternative path for Linux
                analyze_sh = Path(self.ghidra_install_dir) / 'support' / 'analyzeHeadless.sh'
            
            if not analyze_sh.exists():
                raise FileNotFoundError(f"analyzeHeadless not found in {self.ghidra_install_dir}")

            # Create temporary project directory
            with tempfile.TemporaryDirectory() as tmpdir:
                project_path = Path(tmpdir) / 'project'
                project_path.mkdir()

                # Build command
                cmd = [
                    str(analyze_sh),
                    str(project_path),           # project directory
                    'ghidra_project',            # project name
                    '-import', self.binary_path,  # import binary
                    '-scriptPath', str(self.jython_script.parent),
                ]

                if function_filter:
                    cmd.extend(['-postScript', 'disassemble.py', function_filter])
                else:
                    cmd.extend(['-postScript', 'disassemble.py'])

                cmd.extend(['-scriptlog', output_file, '-noanalysis'])

                # Run Ghidra
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env={**os.environ, 'GHIDRA_INSTALL_DIR': self.ghidra_install_dir}
                )

                # Parse output from Jython script
                if result.returncode != 0:
                    raise RuntimeError(f"Ghidra analysis failed: {result.stderr}")

                # Read output file if it exists
                if Path(output_file).exists():
                    with open(output_file, 'r') as f:
                        output_content = f.read()
                        # Try to parse as JSON
                        try:
                            return json.loads(output_content)
                        except json.JSONDecodeError:
                            return {'raw_output': output_content}

                return {'message': 'Analysis completed but no output file generated'}

        except Exception as e:
            return {'error': str(e)}

    def analyze(self, function_address: str = '', function_names: List[str] = None) -> Dict[str, Any]:
        """
        Perform disassembly analysis
        """
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name

            try:
                # Build function filter
                function_filter = ''
                if function_address:
                    function_filter = f'--address={function_address}'
                elif function_names:
                    function_filter = f'--names={",".join(function_names)}'

                # Run Ghidra
                ghidra_result = self.run_ghidra_analysis(output_file, function_filter)

                return {
                    'disassembly': ghidra_result,
                    'summary': f'Disassembled {self.binary_path}'
                }

            finally:
                if Path(output_file).exists():
                    Path(output_file).unlink()

        except Exception as e:
            return {'error': str(e), 'summary': f'Disassembly failed: {str(e)}'}


def main():
    parser = argparse.ArgumentParser(description='Ghidra Disassembler Tool')
    parser.add_argument('--binary', required=True, help='Path to binary file')
    parser.add_argument('--ghidra-dir', required=True, help='Ghidra installation directory')
    parser.add_argument('--function-address', help='Specific function address to disassemble')
    parser.add_argument('--function-names', help='Comma-separated function names to disassemble')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    try:
        disassembler = GhidraDisassembler(args.binary, args.ghidra_dir)
        
        function_names = None
        if args.function_names:
            function_names = args.function_names.split(',')

        analysis_result = disassembler.analyze(args.function_address, function_names)

        output = {
            'data': analysis_result,
            'summary': analysis_result.get('summary', 'Disassembly completed'),
            'metadata': {
                'binary': args.binary,
                'ghidra_version': 'latest',
                'function_address': args.function_address,
                'function_names': args.function_names,
                'ai_next_step': 'Compare disassembly with before/after versions to identify security fixes'
            }
        }

        if args.output_format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(f"Ghidra Disassembly Report")
            print(f"========================")
            print(f"Binary: {args.binary}")
            if args.function_address:
                print(f"Function Address: {args.function_address}")
            if args.function_names:
                print(f"Function Names: {args.function_names}")
            print(f"\n{output['summary']}")

    except Exception as e:
        error_output = {
            'error': str(e),
            'summary': f'Ghidra disassembly failed: {str(e)}',
            'metadata': {'ai_next_step': 'Check Ghidra installation and ensure GHIDRA_INSTALL_DIR is set'}
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
