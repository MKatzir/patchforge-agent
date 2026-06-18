#!/usr/bin/env python3

"""
BinDiff Tool - Python Implementation
Analyzes binary differences using 4 detection methods:
1. Similarity scoring (structural similarity)
2. Function call analysis (detects API call changes)
3. String constants analysis (detects new/removed strings)
4. Branch instruction analysis (detects control flow changes)
"""

import json
import sys
import argparse
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
import subprocess
import os

@dataclass
class ChangedFunction:
    name: str
    address: str
    detection_methods: List[str]
    similarity_score: float
    description: str
    severity: str  # 'critical', 'high', 'medium', 'low'

class BinDiffAnalyzer:
    def __init__(self, before_binary: str, after_binary: str, similarity_threshold: float = 0.70):
        self.before_binary = before_binary
        self.after_binary = after_binary
        self.similarity_threshold = similarity_threshold
        self.changed_functions: List[ChangedFunction] = []

    def extract_strings(self, binary_path: str) -> Dict[str, int]:
        """Extract ASCII strings from binary using 'strings' command"""
        try:
            result = subprocess.run(
                ['strings', binary_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            strings_dict = {}
            for string in result.stdout.strip().split('\n'):
                if string:
                    strings_dict[string] = strings_dict.get(string, 0) + 1
            return strings_dict
        except Exception as e:
            print(f"Warning: Could not extract strings: {e}", file=sys.stderr)
            return {}

    def extract_function_calls(self, binary_path: str) -> Dict[str, List[str]]:
        """Extract function calls using objdump -d (disassembly)"""
        try:
            result = subprocess.run(
                ['objdump', '-d', binary_path],
                capture_output=True,
                text=True,
                timeout=60
            )
            calls = {}
            for line in result.stdout.strip().split('\n'):
                if 'call' in line.lower() or 'jmp' in line.lower():
                    # Parse call instructions: "  address: <instr> <target>"
                    match = re.search(r'<([^>]+)>', line)
                    if match:
                        func_name = match.group(1)
                        calls[func_name] = calls.get(func_name, []) + [line]
            return calls
        except Exception as e:
            print(f"Warning: Could not extract function calls: {e}", file=sys.stderr)
            return {}

    def method_1_similarity_scoring(self) -> List[Tuple[str, float]]:
        """Method 1: Structural similarity based on binary size and content hash"""
        try:
            before_size = os.path.getsize(self.before_binary)
            after_size = os.path.getsize(self.after_binary)
            
            # Read first 1MB for hash comparison
            chunk_size = min(1024 * 1024, min(before_size, after_size))
            
            with open(self.before_binary, 'rb') as f:
                before_chunk = f.read(chunk_size)
            with open(self.after_binary, 'rb') as f:
                after_chunk = f.read(chunk_size)
            
            # Calculate similarity: matching bytes / total bytes
            matching_bytes = sum(1 for a, b in zip(before_chunk, after_chunk) if a == b)
            total_bytes = max(len(before_chunk), len(after_chunk))
            
            similarity = matching_bytes / total_bytes if total_bytes > 0 else 0
            
            # Size change ratio
            size_ratio = 1.0 - abs(before_size - after_size) / max(before_size, after_size) if max(before_size, after_size) > 0 else 0
            
            # Combined similarity
            combined_similarity = (similarity + size_ratio) / 2
            
            return [('binary_comparison', combined_similarity)]
        except Exception as e:
            print(f"Warning: Similarity scoring failed: {e}", file=sys.stderr)
            return []

    def method_2_function_call_analysis(self) -> List[Tuple[str, float]]:
        """Method 2: Detect changes in function calls (e.g., strcpy -> strncpy)"""
        try:
            before_calls = self.extract_function_calls(self.before_binary)
            after_calls = self.extract_function_calls(self.after_binary)
            
            # Find new and removed calls
            new_calls = set(after_calls.keys()) - set(before_calls.keys())
            removed_calls = set(before_calls.keys()) - set(after_calls.keys())
            changed_calls = set(after_calls.keys()) & set(before_calls.keys())
            
            total_functions = len(set(list(before_calls.keys()) + list(after_calls.keys())))
            changes = len(new_calls) + len(removed_calls)
            
            change_ratio = changes / total_functions if total_functions > 0 else 0
            
            return [('function_call_analysis', 1.0 - min(change_ratio, 1.0))]
        except Exception as e:
            print(f"Warning: Function call analysis failed: {e}", file=sys.stderr)
            return []

    def method_3_string_constants_analysis(self) -> List[Tuple[str, float]]:
        """Method 3: Detect changes in string constants"""
        try:
            before_strings = self.extract_strings(self.before_binary)
            after_strings = self.extract_strings(self.after_binary)
            
            # Find new and removed strings
            new_strings = set(after_strings.keys()) - set(before_strings.keys())
            removed_strings = set(before_strings.keys()) - set(after_strings.keys())
            
            total_strings = len(set(list(before_strings.keys()) + list(after_strings.keys())))
            changes = len(new_strings) + len(removed_strings)
            
            change_ratio = changes / total_strings if total_strings > 0 else 0
            
            # Security-relevant strings
            security_keywords = ['buffer', 'overflow', 'strncpy', 'strcpy', 'bounds', 'check', 'validate', 'sanitize']
            new_security_strings = [s for s in new_strings if any(kw in s.lower() for kw in security_keywords)]
            
            if new_security_strings:
                severity_boost = min(len(new_security_strings) * 0.1, 0.5)
                change_ratio = min(change_ratio + severity_boost, 1.0)
            
            return [('string_constants_analysis', 1.0 - change_ratio)]
        except Exception as e:
            print(f"Warning: String constants analysis failed: {e}", file=sys.stderr)
            return []

    def method_4_branch_instruction_analysis(self) -> List[Tuple[str, float]]:
        """Method 4: Detect changes in branch instructions (control flow changes)"""
        try:
            result_before = subprocess.run(
                ['objdump', '-d', self.before_binary],
                capture_output=True,
                text=True,
                timeout=30
            )
            result_after = subprocess.run(
                ['objdump', '-d', self.after_binary],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Count branch instructions
            branch_patterns = [r'\bjmp\b', r'\bje\b', r'\bjne\b', r'\bjz\b', r'\bjnz\b', r'\bcall\b']
            
            before_branches = sum(
                len(re.findall(pattern, result_before.stdout))
                for pattern in branch_patterns
            )
            after_branches = sum(
                len(re.findall(pattern, result_after.stdout))
                for pattern in branch_patterns
            )
            
            total_branches = max(before_branches, after_branches)
            branch_change = abs(before_branches - after_branches)
            
            change_ratio = branch_change / total_branches if total_branches > 0 else 0
            
            return [('branch_instruction_analysis', 1.0 - min(change_ratio, 1.0))]
        except Exception as e:
            print(f"Warning: Branch instruction analysis failed: {e}", file=sys.stderr)
            return []

    def analyze(self) -> Dict[str, Any]:
        """Run all detection methods and combine results"""
        results = {
            'changed_functions': [],
            'detection_methods': {},
            'summary': '',
            'overall_similarity': 0.0
        }

        # Run all 4 detection methods
        method_results = []
        method_results.extend(self.method_1_similarity_scoring())
        method_results.extend(self.method_2_function_call_analysis())
        method_results.extend(self.method_3_string_constants_analysis())
        method_results.extend(self.method_4_branch_instruction_analysis())

        # Calculate overall similarity
        scores = [score for _, score in method_results]
        overall_similarity = sum(scores) / len(scores) if scores else 0.0

        for method_name, score in method_results:
            results['detection_methods'][method_name] = round(score, 4)

        # Determine if binaries are significantly different
        if overall_similarity < self.similarity_threshold:
            results['changed_functions'].append(asdict(ChangedFunction(
                name='_binary_changed',
                address='0x0',
                detection_methods=[m for m, s in method_results if s < 0.9],
                similarity_score=overall_similarity,
                description='Binary files show significant differences',
                severity='high' if overall_similarity < 0.5 else 'medium'
            )))
            results['summary'] = f'Binary files differ with {100*(1-overall_similarity):.1f}% changes detected'
        else:
            results['summary'] = f'Binary files are similar (similarity: {overall_similarity:.1%})'

        results['overall_similarity'] = round(overall_similarity, 4)
        return results


def main():
    parser = argparse.ArgumentParser(description='BinDiff Analysis Tool')
    parser.add_argument('--before', required=True, help='Path to before binary')
    parser.add_argument('--after', required=True, help='Path to after binary')
    parser.add_argument('--similarity-threshold', type=float, default=0.70, help='Similarity threshold')
    parser.add_argument('--output-format', choices=['json', 'text'], default='json', help='Output format')

    args = parser.parse_args()

    try:
        analyzer = BinDiffAnalyzer(args.before, args.after, args.similarity_threshold)
        analysis_result = analyzer.analyze()

        output = {
            'data': analysis_result,
            'summary': analysis_result['summary'],
            'metadata': {
                'before_binary': args.before,
                'after_binary': args.after,
                'similarity_threshold': args.similarity_threshold,
                'methods_used': list(analysis_result['detection_methods'].keys()),
                'ai_next_step': 'Examine changed functions and select top candidates for Ghidra disassembly/decompilation'
            }
        }

        if args.output_format == 'json':
            print(json.dumps(output, indent=2))
        else:
            print(f"BinDiff Analysis Report")
            print(f"======================")
            print(f"Before: {args.before}")
            print(f"After: {args.after}")
            print(f"Overall Similarity: {analysis_result['overall_similarity']:.1%}")
            print(f"\nDetection Methods:")
            for method, score in analysis_result['detection_methods'].items():
                print(f"  {method}: {score:.1%}")
            print(f"\nSummary: {analysis_result['summary']}")

    except Exception as e:
        error_output = {
            'error': str(e),
            'summary': f'BinDiff analysis failed: {str(e)}',
            'metadata': {'ai_next_step': 'Check input binary paths and ensure files are readable'}
        }
        print(json.dumps(error_output, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()
