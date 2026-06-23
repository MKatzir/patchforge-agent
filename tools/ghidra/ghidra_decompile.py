import json, sys, os, argparse, tempfile, subprocess
from pathlib import Path

class GhidraDecompiler:
    def __init__(self, binary_path, ghidra_dir):
        self.binary_path = binary_path
        self.ghidra_dir = ghidra_dir
        self.jython_script = Path(__file__).parent / 'ghidra_scripts' / 'decompile.py'

    def run_ghidra(self, output_file, addr='', names=None):
        analyze_sh = Path(self.ghidra_dir) / 'support' / 'analyzeHeadless'
        if not analyze_sh.exists(): 
            analyze_sh = Path(self.ghidra_dir) / 'support' / 'analyzeHeadless.sh'
        
        with tempfile.TemporaryDirectory() as tmpdir:
            proj = Path(tmpdir) / 'proj'
            proj.mkdir()
            cmd = [str(analyze_sh), str(proj), 'proj', '-import', self.binary_path, 
                   '-scriptPath', str(self.jython_script.parent), '-postScript', self.jython_script.name]
            
            env = os.environ.copy()
            env['GHIDRA_OUTPUT_FILE'] = output_file
            if addr: env['GHIDRA_FUNCTION_ADDRESS'] = addr
            if names: env['GHIDRA_FUNCTION_NAMES'] = ','.join(names)
            
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=300, env=env)
            if res.returncode != 0:
                raise RuntimeError(f"Ghidra failed: {res.stdout}\n{res.stderr}")
                
            if Path(output_file).exists():
                with open(output_file, 'r') as f:
                    content = f.read()
                    try: return json.loads(content)
                    except: return {'raw_output': content}
            return {'raw_output': ''}

    def analyze(self, addr='', names=None):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            out_file = f.name
        try:
            result = self.run_ghidra(out_file, addr, names)
            return {'decompilation': result, 'summary': f"Decompiled {self.binary_path}"}
        except Exception as e:
            return {'error': str(e)}
        finally:
            if Path(out_file).exists(): Path(out_file).unlink()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--binary', required=True)
    parser.add_argument('--ghidra-dir', required=True)
    parser.add_argument('--function-address')
    parser.add_argument('--function-names')
    parser.add_argument('--output-format', default='json')
    args = parser.parse_args()
    
    try:
        d = GhidraDecompiler(args.binary, args.ghidra_dir)
        names = args.function_names.split(',') if args.function_names else None
        res = d.analyze(args.function_address, names)
        
        output = {
            'data': res,
            'summary': res.get('summary', 'Decompilation completed'),
            'metadata': {'binary': args.binary, 'function_address': args.function_address}
        }
        print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__': main()
