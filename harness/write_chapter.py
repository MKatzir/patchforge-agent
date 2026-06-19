#!/usr/bin/env python3
"""
Chapter Writer - Saves raw Ghidra output to a numbered chapter file.
Usage: python3 write_chapter.py <chapter_id> <source_path>
"""

import json
import os
import sys

CHAPTER_DB = os.path.join(os.path.dirname(__file__), 'db')

def write_chapter(chapter_id: str, source_path: str) -> None:
    os.makedirs(CHAPTER_DB, exist_ok=True)
    chapter_file = os.path.join(CHAPTER_DB, f'chapter_{chapter_id}.json')

    if not os.path.exists(source_path):
        print(f'ERROR: source file not found: {source_path}', file=sys.stderr)
        sys.exit(1)

    with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {'raw': content}

    with open(chapter_file, 'w', encoding='utf-8') as f:
        json.dump({
            'chapter_id': chapter_id,
            'source': source_path,
            'data': data
        }, f, indent=2)

    print(f'Chapter {chapter_id} written to {chapter_file}')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(f'Usage: python3 {sys.argv[0]} <chapter_id> <source_path>')
        sys.exit(1)
    write_chapter(sys.argv[1], sys.argv[2])