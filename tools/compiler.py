#!/usr/bin/env python3

"""
Compiler Tool - Python Implementation
Compiles C/C++ source code using GCC/G++ with configurable flags
"""

import json
import sys
import os
import argparse
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any

class Compiler:
    def __init__(self, source_path: str, output_path: str = '',
                 compiler: str = 'gcc', flags: List[str] = None,
                 optimization: str = 'O0', arch: str = 'x86_64'):
        self.source_path = source_path
        self.output_path = output_path or Path(source_path).stem
        self.compiler = compiler
        self.flags = flags or []
        self.optimization = f'-{optimization}' if not optimization.startswith('-') else optimization
        self.arch = arch

    def compile(self) -> Dict[str, Any]:
        """Compile the source file"""
        try:
            if not Path(self.source_path).exists():
                raise FileNotFoundError(f"Source file not found: {self.source_path}")

            ext = Path(self.source_path).suffix.lower()
            if ext not in ('.c', '.cpp', '.cc', '.cxx', '.s', '.asm'):
                raise ValueError(f"Unsupported source file extension: {ext}")

            # Determine default compiler by extension if not overridden
            compiler = self.compiler
            if compiler == 'gcc' and ext in ('.cpp', '.cc', '.cxx'):
                compiler = 'g++'

            # Build command
            cmd = [compiler, self.source_path, '-o', self.output_path, self.optimization]

            # Add architecture flags
            if self.arch == 'x86':
                cmd.extend(['-m32'])
            elif self.arch == 'x86_64':
                cmd.extend(['-m64'])
            elif self.arch == 'arm':
                cmd.extend(['-marm'])
            elif self.arch == 'arm64':
                cmd.extend(['-march=armv8-a'])

            # Add extra flags
            cmd.extend(self.flags)

            # Run compilation
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode == 0:
                return {
                    'output_path': os.path.abspath(self.output_path),
                    'compiler': compiler,
                    'flags': cmd[1:],
                    'arch': self.arch,
                    'warnings': result.stderr.strip(),
                    'binary_size': os.path.getsize(self.output_path) if os.path.exists(self.output_path) else 0,
                    'summary': f'Compilation successful: {self.source_path} -> {self.output_path}'
                }
            else:
                return {
                    'error': result.stderr.strip(),
                    'compiler': compiler,
                    'flags': cmd[1:],
                    'summary': f'Compilation failed: {result.stderr.strip()}'
                }

        except Exception as e:
            return {'error': str(e), 'summary': f'Compilation error: {str(e)}'}

    def get_file_info(self) -> Dict[str, Any]:
        """Get information about the compiled binary"""
        try:
            if not os.path.exists(self.output_path):
                return {}

            result = subprocess.run(
                ['file', self.output_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            return {
                'file_type': result.stdout.strip(),
                'size_bytes': os.path.getsize(self.output_path),
            }

        except Exception as e:
            return {'error': str(e)}


def main():
    parser = argparse.ArgumentParser(description='Compiler Tool')
    parser.add_argument('--source', required=True, help='Path to source file')
    parser.add_argument('--output', help='Output binary path')
    parser.add_argument('--compiler', choices=['gcc', 'g++'], default='gcc', help='Compiler to use')
    parser.add_argument('--flags', default='', help='Additional compiler flags (space-separated)')
    parser.add_argument('--optimization', choices=['O0', 'O1', 'O2', 'O3', 'Os'], default='O0',
                        help='Optimization level')
    parser.add_argument('--arch', choices=['x86', 'x86_64', 'arm', 'arm64'], default='x86_64',
                        help='Target architecture')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json')

    args = parser.parse_args()

    try:
        flags = [f.strip() for f in args.flags.split() if f.strip()] if args.flags else []

        compiler = Compiler(
            source_path=args.source,
            output_path=args.output or '',
            compiler=args.compiler,
            flags=flags,
            optimization=args.optimization,
            arch=args.arch
        )

        compile_result = compiler.compile()
        file_info = compiler.get_file_info() if compile_result.get('output_path') else {}

        output = {
            'data': {
                'compilation': compile_result,
                'file_info': file_info
            },
            'summary': compile_result.get('summary', 'Compilation completed'),
            'metadata': {
                'source': args.source,
                'output': args.output or Path(args.source).stem,
                'compiler': args.compiler,
                'optimization': args.optimization,
                'arch': args.arch,
                'ai_next_step': 'Use compiled binary for BinDiff analysis or exploit testing'
            }
        }

        if args.output_format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(f"Compiler Report")
            print(f"==============")
            print(f"Source: {args.source}")
            print(f"Output: {output.get('data', {}).get('compilation', {}).get('output_path', args.output or Path(args.source).stem)}")
            print(f"Status: {'Success' if compile_result.get('output_path') else 'Failed'}")
            if compile_result.get('output_path'):
                print(f"Size: {file_info.get('size_bytes', 0)} bytes")
            if compile_result.get('error'):
                print(f"Error: {compile_result['error']}")

    except Exception as e:
        error_output = {
            'error': str(e),
            'summary': f'Compiler failed: {str(e)}',
            'metadata': {'ai_next_step': 'Check source file and GCC/G++ installation'}
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
