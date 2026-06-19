#!/usr/bin/env python3
"""
Chapter Reader - Reads a saved chapter file and prints its contents.
Usage: python3 read_chapter.py <chapter_id>
"""

import json
import os
import sys

CHAPTER_DB = os.path.join(os.path.dirname(__file__), 'db')

def read_chapter(chapter_id: str) -> None:
    chapter_file = os.path.join(CHAPTER_DB, f'chapter_{chapter_id}.json')

    if not os.path.exists(chapter_file):
        print(f'ERROR: chapter {chapter_id} not found at {chapter_file}', file=sys.stderr)
        sys.exit(1)

    with open(chapter_file, 'r', encoding='utf-8') as f:
        chapter = json.load(f)

    print(json.dumps(chapter, indent=2))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f'Usage: python3 {sys.argv[0]} <chapter_id>')
        sys.exit(1)
    read_chapter(sys.argv[1])