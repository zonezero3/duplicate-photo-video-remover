import os
import hashlib
import csv
from pathlib import Path

# --- Configurations ---
# Path 1: Reference directory (Files here are preserved)
# Example: "D:/Photos/Original_Backup"
REFERENCE_DIR = r"D:/Photos/Reference" 

# Path 2: Target directory to clean (Files here will be deleted if duplicates exist in Path 1)
# Example: "E:/New_Photos/To_Sort"
TARGET_DIR = r"D:/Photos/Target_To_Clean"

# Log file name
LOG_FILE = "deletion_log.csv"

# List of file extensions to scan (Photos and Videos)
EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp', '.heic',
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.ts'
}

def get_file_hash(path):
    """Reads file content and generates MD5 hash (for content comparison)."""
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            # Read in 64KB chunks to handle large files
            while buf := f.read(65536):
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception as e:
        print(f"Hash calculation error ({path}): {e}")
        return None

def find_media_files(directory):
    """Finds all media files under the specified directory."""
    for root, _, files in os.walk(directory):
        for file in files:
            ext = Path(file).suffix.lower()
            if ext in EXTENSIONS:
                yield os.path.join(root, file)

def main():
    print(">>> Duplicate File Remover (Folder Comparison)")
    print(f"1. Reference Folder (Preserved): {REFERENCE_DIR}")
    print(f"2. Target Folder (Deletion): {TARGET_DIR}")
    print("-" * 70)

    if not os.path.exists(REFERENCE_DIR) or not os.path.exists(TARGET_DIR):
        print("[Error] Path does not exist. Please check the path settings at the top of the code.")
        return

    # 1. Scan Reference Directory (Path 1) and store hashes
    print(">>> Step 1: Analyzing files in Reference Folder...")
    reference_hashes = {}
    count = 0
    
    for path in find_media_files(REFERENCE_DIR):
        f_hash = get_file_hash(path)
        if f_hash:
            # Store hash as key, path as value (only one instance needed for duplicates)
            reference_hashes[f_hash] = path
            count += 1
            if count % 100 == 0:
                print(f"   - {count} files indexed...", end='\r')
    
    print(f"\n   -> Analysis complete for {count} reference files.\n")

    # 2. Scan Target Directory (Path 2) and delete duplicates
    print(">>> Step 2: Scanning Target Folder and deleting duplicates...")
    deleted_files = []
    deleted_size = 0
    
    # Prepare CSV log file
    with open(LOG_FILE, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['Status', 'Deleted_File_Path', 'Kept_Original_Path', 'Size_Bytes']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for path in find_media_files(TARGET_DIR):
            f_hash = get_file_hash(path)
            if not f_hash:
                continue

            # Check if the same hash exists in the reference directory
            if f_hash in reference_hashes:
                original_path = reference_hashes[f_hash]
                
                # Skip if the path is exactly the same file (same folder)
                if os.path.abspath(path) == os.path.abspath(original_path):
                    continue

                try:
                    file_size = os.path.getsize(path)
                    os.remove(path) # Delete file
                    
                    deleted_size += file_size
                    deleted_files.append(path)
                    
                    # Log record
                    writer.writerow({
                        'Status': 'Deleted',
                        'Deleted_File_Path': path,
                        'Kept_Original_Path': original_path,
                        'Size_Bytes': file_size
                    })
                    print(f"[Deleted] {path}")
                    
                except Exception as e:
                    print(f"[Delete Failed] {path} : {e}")

    # 3. Result Report
    print("-" * 70)
    print("Task Completed!")
    print(f"- Total deleted files: {len(deleted_files)}")
    print(f"- Disk space reclaimed: {deleted_size / (1024*1024):.2f} MB")
    print(f"- Detailed log file: {os.path.abspath(LOG_FILE)}")
    print("-" * 70)

if __name__ == "__main__":
    main()