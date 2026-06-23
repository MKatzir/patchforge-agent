#!/usr/bin/env python3
import json, sys, argparse, subprocess, os, tempfile, sqlite3
from pathlib import Path

class OfficialBinDiff:
    def __init__(self, before_bin, after_bin, ghidra_dir, threshold):
        self.before_bin = Path(before_bin).resolve()
        self.after_bin = Path(after_bin).resolve()
        self.ghidra_dir = Path(ghidra_dir)
        self.threshold = threshold
        self.analyze_sh = self.ghidra_dir / 'support' / 'analyzeHeadless'
        self.jython_script = Path(__file__).parent / 'ghidra_scripts' / 'export_binexport.py'

    def export_binexport(self, binary_path, output_binexport):
        with tempfile.TemporaryDirectory() as tmpdir:
            proj = Path(tmpdir) / 'proj'
            proj.mkdir()
            cmd = [
                str(self.analyze_sh), str(proj), 'proj', 
                '-import', str(binary_path), 
                '-scriptPath', str(self.jython_script.parent), 
                '-postScript', self.jython_script.name
            ]
            env = os.environ.copy()
            env['GHIDRA_OUTPUT_FILE'] = str(output_binexport)
            
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            if not output_binexport.exists():
                raise RuntimeError(f"Failed to export {binary_path.name}:\n{res.stdout}\n{res.stderr}")

    def run_bindiff(self, before_export, after_export, out_dir):
        cmd = [
            'bindiff',
            f'--primary={before_export}',
            f'--secondary={after_export}',
            f'--output_dir={out_dir}'
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"BinDiff engine failed:\n{res.stderr}")
            
        # BinDiff names the SQLite DB based on the input files
        expected_db = out_dir / f"{before_export.stem}_vs_{after_export.stem}.BinDiff"
        if not expected_db.exists():
            # Fallback if naming convention differs
            dbs = list(out_dir.glob('*.BinDiff'))
            if dbs: return dbs
            raise RuntimeError("BinDiff database not generated.")
        return expected_db

    def parse_sqlite(self, db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Query functions where similarity is below threshold. 
        # address1 is old binary, address2 is new binary.
        cursor.execute('''
            SELECT address1, address2, similarity, confidence, name2 
            FROM function 
            WHERE similarity < ? AND address2 IS NOT NULL
            ORDER BY similarity ASC
        ''', (self.threshold,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "old_address": hex(row) if row else None,
                "address": hex(row),  # This is the target for the new binary
                "similarity": round(row, 4),
                "confidence": round(row, 4),
                "name": row
            })
            
        # Count total functions for context
        cursor.execute('SELECT COUNT(*) FROM function')
        total = cursor.fetchone()
        conn.close()
        return results, total

    def analyze(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            before_export = tmp_path / f"{self.before_bin.name}.BinExport"
            after_export = tmp_path / f"{self.after_bin.name}.BinExport"
            
            # Step 1: Export both binaries
            self.export_binexport(self.before_bin, before_export)
            self.export_binexport(self.after_bin, after_export)
            
            # Step 2: Run BinDiff
            db_path = self.run_bindiff(before_export, after_export, tmp_path)
            
            # Step 3: Parse results
            suspicious_functions, total_funcs = self.parse_sqlite(db_path)
            
            return {
                "overall_similarity": "N/A (See individual functions)",
                "total_functions_analyzed": total_funcs,
                "suspicious_functions": suspicious_functions,
                "summary": f"Found {len(suspicious_functions)} changed/new functions out of {total_funcs}."
            }

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', required=True)
    parser.add_argument('--after', required=True)
    parser.add_argument('--similarity-threshold', type=float, default=0.95)
    parser.add_argument('--min-block-size', type=int) # Ignored in official BinDiff
    parser.add_argument('--opcode-only', action='store_true') # Ignored in official BinDiff
    args = parser.parse_args()

    ghidra_dir = os.environ.get("GHIDRA_INSTALL_DIR", "/app/ghidra_install")

    try:
        analyzer = OfficialBinDiff(args.before, args.after, ghidra_dir, args.similarity_threshold)
        result = analyzer.analyze()

        output = {
            'data': result,
            'summary': result['summary'],
            'metadata': {'ai_next_step': 'Send suspicious_functions addresses to Ghidra decompiler'}
        }
        print(json.dumps(output, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}))
        sys.exit(1)

if __name__ == '__main__':
    main()
