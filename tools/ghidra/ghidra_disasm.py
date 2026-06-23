"""
Ghidra Disassembler Tool - Python Orchestrator
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

    def run_ghidra_analysis(self, output_file: str, function_address: str = '', function_names: List[str] = None) -> Dict[str, Any]:
        try:
            analyze_sh = Path(self.ghidra_install_dir) / 'support' / 'analyzeHeadless'
            if not analyze_sh.exists():
                analyze_sh = Path(self.ghidra_install_dir) / 'support' / 'analyzeHeadless.sh'
            if not analyze_sh.exists():
                raise FileNotFoundError(f"analyzeHeadless not found in {self.ghidra_install_dir}")

            with tempfile.TemporaryDirectory() as tmpdir:
                project_path = Path(tmpdir) / 'project'
                project_path.mkdir()

                cmd = [
                    str(analyze_sh),
                    str(project_path),
                    'ghidra_project',
                    '-import', self.binary_path,
                    '-scriptPath', str(self.jython_script.parent),
                    '-postScript', self.jython_script.name
                ]

                # Sneak the arguments past Java using the environment variables
                env = os.environ.copy()
                env['GHIDRA_OUTPUT_FILE'] = output_file
                if function_address:
                    env['GHIDRA_FUNCTION_ADDRESS'] = function_address
                if function_names:
                    env['GHIDRA_FUNCTION_NAMES'] = ','.join(function_names)

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,
                    env=env
                )

                if result.returncode != 0:
                    raise RuntimeError(f"Ghidra analysis failed: STDOUT: {result.stdout}\nSTDERR: {result.stderr}")

                if Path(output_file).exists():
                    with open(output_file, 'r') as f:
                        output_content = f.read()
                        try:
                            return json.loads(output_content)
                        except json.JSONDecodeError:
                            return {'raw_output': output_content}

                return {'message': 'Analysis completed but no output file generated', 'stdout': result.stdout}

        except Exception as e:
            return {'error': str(e)}

    def analyze(self, function_address: str = '', function_names: List[str] = None) -> Dict[str, Any]:
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                output_file = f.name

            try:
                # Pass the variables directly, no CLI strings!
                ghidra_result = self.run_ghidra_analysis(output_file, function_address, function_names)
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
    parser.add_argument('--binary', required=True)
    parser.add_argument('--ghidra-dir', required=True)
    parser.add_argument('--function-address')
    parser.add_argument('--function-names')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json')

    args = parser.parse_args()

    try:
        disassembler = GhidraDisassembler(args.binary, args.ghidra_dir)
        function_names = args.function_names.split(',') if args.function_names else None
        analysis_result = disassembler.analyze(args.function_address, function_names)

        output = {
            'data': analysis_result,
            'summary': analysis_result.get('summary', 'Disassembly completed'),
            'metadata': {
                'binary': args.binary,
                'function_address': args.function_address,
                'ai_next_step': 'Analyze output'
            }
        }
        print(json.dumps(output, indent=2))
    except Exception as e:
        error_output = {'error': str(e), 'summary': f'Failed: {str(e)}'}
        print(json.dumps(error_output, indent=2))
        sys.exit(1)

if __name__ == '__main__':
    main()
