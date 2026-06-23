#!/usr/bin/env python3

"""
Symbol Analyzer Tool - Python Implementation
Extracts and analyzes symbols using `nm` and `objdump` commands
"""

import json
import sys
import os
import argparse
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Tuple

class SymbolAnalyzer:
    def __init__(self, binary_path: str, symbol_types: str = '',
                 demangle: bool = True):
        self.binary_path = binary_path
        self.symbol_types = symbol_types
        self.demangle = demangle

    def extract_nm_symbols(self) -> List[Dict[str, str]]:
        """Extract symbols using the `nm` command"""
        try:
            cmd = ['nm']

            if self.demangle:
                cmd.append('-C')

            cmd.extend(['-S', self.binary_path])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                raise RuntimeError(f"nm failed: {result.stderr.strip()}")

            symbols = []
            type_chars = {'T','t','D','d','B','b','U','u','W','w','A','a','C','c',
                          'G','g','S','s','I','i','N','n','O','o','P','p','R','r',
                          'V','v','Z','z'}

            for line in result.stdout.strip().split('\n'):
                if not line.strip():
                    continue
                parts = line.split()
                # nm -C -S output patterns:
                # 4 parts: address, size, type, name (defined with size)
                # 3 parts: address, type, name (defined without size)
                # 2 parts: type, name (undefined, no address)
                if len(parts) >= 4:
                    symbols.append({
                        'address': parts[0],
                        'size': parts[1],
                        'type': parts[2],
                        'name': ' '.join(parts[3:])
                    })
                elif len(parts) == 3 and parts[1] in type_chars:
                    symbols.append({
                        'address': parts[0],
                        'size': '',
                        'type': parts[1],
                        'name': parts[2]
                    })
                elif len(parts) >= 2:
                    symbols.append({
                        'address': '',
                        'size': '',
                        'type': parts[0],
                        'name': ' '.join(parts[1:])
                    })

            return symbols

        except Exception as e:
            raise RuntimeError(f"nm extraction failed: {str(e)}")

    def extract_objdump_symbols(self) -> List[Dict[str, Any]]:
        """Extract symbols using `objdump -t`"""
        try:
            cmd = ['objdump', '-t']

            if self.demangle:
                cmd.append('-C')

            cmd.append(self.binary_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return []

            sections = []
            for line in result.stdout.strip().split('\n'):
                if not line.strip() or line.startswith('SYMBOL TABLE:'):
                    continue

                match = re.match(
                    r'^([0-9a-fA-F]+)\s+([lg\s])\s+([\w\s]+?)\s+([0-9a-fA-F]+)\s+(.+)$',
                    line
                )
                if match:
                    sections.append({
                        'value': match.group(1),
                        'flags': match.group(2).strip(),
                        'type': match.group(3).strip(),
                        'size': match.group(4),
                        'name': match.group(5).strip()
                    })

            return sections

        except Exception as e:
            return []

    def analyze(self) -> Dict[str, Any]:
        """Analyze symbol tables"""
        try:
            if not Path(self.binary_path).exists():
                raise FileNotFoundError(f"Binary not found: {self.binary_path}")

            # Get symbols from nm
            nm_symbols = self.extract_nm_symbols()
            objdump_sections = self.extract_objdump_symbols()

            # Categorize symbols by type
            defined_functions = [s for s in nm_symbols if s['type'] in ('T', 't', 'W', 'w')]
            undefined_functions = [s for s in nm_symbols if s['type'] == 'U']
            data_symbols = [s for s in nm_symbols if s['type'] in ('D', 'd', 'B', 'b', 'G', 'g')]

            # Detect security-relevant symbols
            security_patterns = {
                'string_functions': ['strcpy', 'strncpy', 'strcat', 'strncat', 'strlen', 'strcmp',
                                     'strncmp', 'strdup', 'strndup', 'memcpy', 'memmove', 'memset',
                                     'memcmp'],
                'format_functions': ['printf', 'sprintf', 'snprintf', 'fprintf', 'scanf', 'sscanf'],
                'memory_functions': ['malloc', 'calloc', 'realloc', 'free', 'mmap', 'munmap'],
                'io_functions': ['read', 'write', 'open', 'close', 'fread', 'fwrite', 'fopen', 'fclose',
                                 'send', 'recv', 'accept', 'bind', 'listen', 'connect'],
                'auth_functions': ['login', 'authenticate', 'authorize', 'verify', 'check_password',
                                   'validate_user', 'encrypt', 'decrypt', 'hash']
            }

            security_symbols = {}
            for category, patterns in security_patterns.items():
                matches = [
                    s['name'] for s in nm_symbols
                    if any(p in s['name'] for p in patterns)
                ]
                if matches:
                    security_symbols[category] = matches[:20]

            # Filter by requested types
            if self.symbol_types:
                type_filter = set(self.symbol_types.split(','))
                nm_symbols = [s for s in nm_symbols if s['type'] in type_filter]

            return {
                'total_symbols': len(nm_symbols),
                'defined_functions': len(defined_functions),
                'undefined_functions': len(undefined_functions),
                'data_symbols': len(data_symbols),
                'function_names': [s['name'] for s in defined_functions[:200]],
                'imported_functions': [s['name'] for s in undefined_functions[:200]],
                'security_relevant': security_symbols,
                'sections': objdump_sections[:50],
                'sample_symbols': nm_symbols[:100],
                'summary': f'Found {len(nm_symbols)} symbols ({len(defined_functions)} defined functions, {len(undefined_functions)} imports) in {self.binary_path}'
            }

        except Exception as e:
            return {'error': str(e), 'summary': f'Symbol analysis failed: {str(e)}'}


def main():
    parser = argparse.ArgumentParser(description='Symbol Analyzer Tool')
    parser.add_argument('--binary', required=True, help='Path to binary file')
    parser.add_argument('--symbol-types', help='Filter by symbol types (comma-separated, e.g., T,t,U)')
    parser.add_argument('--demangle', action='store_true', default=True, help='Demangle C++ symbols')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json')

    args = parser.parse_args()

    try:
        analyzer = SymbolAnalyzer(
            binary_path=args.binary,
            symbol_types=args.symbol_types or '',
            demangle=args.demangle
        )

        analysis_result = analyzer.analyze()

        output = {
            'data': analysis_result,
            'summary': analysis_result.get('summary', 'Symbol analysis completed'),
            'metadata': {
                'binary': args.binary,
                'symbol_types_filter': args.symbol_types,
                'demangle': args.demangle,
                'ai_next_step': 'Cross-reference symbol changes with BinDiff results to identify security-relevant functions'
            }
        }

        if args.output_format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(f"Symbol Analyzer Report")
            print(f"======================")
            print(f"Binary: {args.binary}")
            print(f"Total Symbols: {analysis_result.get('total_symbols', 0)}")
            print(f"Defined Functions: {analysis_result.get('defined_functions', 0)}")
            print(f"Undefined Functions (Imports): {analysis_result.get('undefined_functions', 0)}")
            print(f"Data Symbols: {analysis_result.get('data_symbols', 0)}")
            if analysis_result.get('security_relevant'):
                for cat, syms in analysis_result['security_relevant'].items():
                    print(f"  {cat}: {', '.join(syms[:5])}")

    except Exception as e:
        error_output = {
            'error': str(e),
            'summary': f'Symbol analysis failed: {str(e)}',
            'metadata': {'ai_next_step': 'Check binary and nm/objdump availability'}
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
