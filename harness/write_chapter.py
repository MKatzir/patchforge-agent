import sys
import json
import os

def main():
    if len(sys.argv) != 3:
        print("Usage: python3 write_chapter.py <chapter_id> <path_to_raw_output>")
        sys.exit(1)

    chapter_id = sys.argv[1]
    source_path = sys.argv[2]
    db_dir = "db"

    os.makedirs(db_dir, exist_ok=True)
    target_path = os.path.join(db_dir, f"{chapter_id}.json")

    try:
        with open(source_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump({"chapter_id": chapter_id, "content": content}, f, indent=4)
            
        print(f"Success: Saved {chapter_id} to Context DB.")
    except Exception as e:
        print(f"Error writing chapter: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
