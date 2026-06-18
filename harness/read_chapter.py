import sys
import json
import os

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 read_chapter.py <chapter_id>")
        sys.exit(1)

    chapter_id = sys.argv[1]
    db_path = os.path.join("db", f"{chapter_id}.json")

    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        print(f"--- START {chapter_id} ---")
        print(data.get("content", "No content found."))
        print(f"--- END {chapter_id} ---")
    except FileNotFoundError:
        print(f"Error: {chapter_id} not found in Context DB.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading chapter: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
