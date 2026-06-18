#!/usr/bin/env python3

"""
String Analyzer Tool - Python Implementation
Extracts ASCII and Unicode strings from binaries using the `strings` command
Analyzes string content for security-relevant patterns
"""

import json
import sys
import os
import argparse
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any

class StringAnalyzer:
    def __init__(self, binary_path: str, min_length: int = 4,
                 encoding: str = 'all', search_pattern: str = ''):
        self.binary_path = binary_path
        self.min_length = min_length
        self.encoding = encoding
        self.search_pattern = search_pattern

    def extract_strings(self) -> Dict[str, Any]:
        """Extract strings using the Linux `strings` command"""
        try:
            if not Path(self.binary_path).exists():
                raise FileNotFoundError(f"Binary not found: {self.binary_path}")

            cmd = ['strings']

            # Encoding flags
            if self.encoding == 'ascii':
                cmd.append('-a')
            elif self.encoding == 'unicode':
                cmd.extend(['-e', 'l'])
            elif self.encoding == 'utf16':
                cmd.extend(['-e', 'L'])
            elif self.encoding == 'all':
                cmd.extend(['-a'])

            # Minimum length
            if self.min_length:
                cmd.extend(['-n', str(self.min_length)])

            cmd.append(self.binary_path)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return {
                    'error': result.stderr.strip(),
                    'summary': f'strings command failed: {result.stderr.strip()}'
                }

            all_strings = [s.strip() for s in result.stdout.split('\n') if s.strip()]

            # Filter by search pattern if provided
            if self.search_pattern:
                try:
                    pattern = re.compile(self.search_pattern, re.IGNORECASE)
                    filtered = [s for s in all_strings if pattern.search(s)]
                except re.error:
                    filtered = [s for s in all_strings if self.search_pattern.lower() in s.lower()]
            else:
                filtered = all_strings

            return self._analyze_strings(filtered, all_strings)

        except Exception as e:
            return {'error': str(e), 'summary': f'Failed to extract strings: {str(e)}'}

    def _analyze_strings(self, strings: List[str], all_strings: List[str]) -> Dict[str, Any]:
        """Analyze extracted strings for security-relevant patterns"""
        # Security-relevant string categories
        security_patterns = {
            'buffer_overflow': [r'(?i)(buffer|overflow|stack|heap)'],
            'bounds_checking': [r'(?i)(bounds|limit|length|size|count)'],
            'error_messages': [r'(?i)(error|fail|invalid|abort|denied)'],
            'validation': [r'(?i)(validate|check|verify|sanitize|allow)'],
            'format_strings': [r'%[dsxun]'],
            'function_names': [r'(?i)(strcpy|strncpy|sprintf|snprintf|memcpy|memmove|gets|fgets)'],
            'paths': [r'^/(etc|usr|var|tmp|dev|proc|sys)/'],
            'ip_addresses': [r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}'],
            'urls': [r'https?://'],
        }

        categories: Dict[str, List[str]] = {}
        for category, patterns in security_patterns.items():
            matches = []
            for s in strings:
                for pattern in patterns:
                    if re.search(pattern, s):
                        matches.append(s)
                        break
            if matches:
                categories[category] = matches[:20]

        # Statistics
        total = len(all_strings)
        filtered_count = len(strings)
        unique = len(set(all_strings))

        # Longest strings
        sorted_strings = sorted(strings, key=len, reverse=True)
        longest_strings = sorted_strings[:10] if sorted_strings else []

        return {
            'total_strings': total,
            'unique_strings': unique,
            'filtered_count': filtered_count if self.search_pattern else total,
            'min_length': self.min_length,
            'encoding': self.encoding,
            'search_pattern': self.search_pattern or None,
            'categories': categories,
            'longest_strings': longest_strings,
            'sample_strings': sorted_strings[:100] if len(sorted_strings) <= 100 else sorted_strings[:100],
            'summary': f'Found {total} strings ({unique} unique) in {self.binary_path}'
        }


def main():
    parser = argparse.ArgumentParser(description='String Analyzer Tool')
    parser.add_argument('--binary', required=True, help='Path to binary file')
    parser.add_argument('--min-length', type=int, default=4, help='Minimum string length')
    parser.add_argument('--encoding', choices=['all', 'ascii', 'unicode', 'utf16'], default='all',
                        help='String encoding')
    parser.add_argument('--search-pattern', help='Regex pattern to filter strings')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json')

    args = parser.parse_args()

    try:
        analyzer = StringAnalyzer(
            binary_path=args.binary,
            min_length=args.min_length,
            encoding=args.encoding,
            search_pattern=args.search_pattern or ''
        )

        analysis_result = analyzer.extract_strings()

        output = {
            'data': analysis_result,
            'summary': analysis_result.get('summary', 'String analysis completed'),
            'metadata': {
                'binary': args.binary,
                'min_length': args.min_length,
                'encoding': args.encoding,
                'search_pattern': args.search_pattern,
                'categories_found': list(analysis_result.get('categories', {}).keys()),
                'ai_next_step': 'Compare strings between before/after versions to identify security-relevant changes'
            }
        }

        if args.output_format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(f"String Analyzer Report")
            print(f"=====================")
            print(f"Binary: {args.binary}")
            print(f"Total Strings: {analysis_result.get('total_strings', 0)}")
            print(f"Unique Strings: {analysis_result.get('unique_strings', 0)}")
            print(f"\nCategories Found:")
            for cat, strs in analysis_result.get('categories', {}).items():
                print(f"  {cat}: {len(strs)} occurrences")

    except Exception as e:
        error_output = {
            'error': str(e),
            'summary': f'String analysis failed: {str(e)}',
            'metadata': {'ai_next_step': 'Check binary file and strings command availability'}
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
