import os
import hashlib
import csv
import shutil
from pathlib import Path
from datetime import datetime
from PIL import Image
from PIL.ExifTags import TAGS

# --- Configurations ---
TARGET_DRIVE = "D:/D"             # Source directory to scan
BACKUP_DIR = "D:/Duplicate_Backup" # Directory where duplicates will be moved
LOG_FILE = "duplicate_media_report.csv" # Detailed report filename

# Supported file extensions for photos and videos
EXTENSIONS = {
    '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', # Photos
    '.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv'    # Videos
}

def get_file_hash(path):
    """Generate MD5 hash to determine file content identity."""
    hasher = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            while buf := f.read(65536):
                hasher.update(buf)
        return hasher.hexdigest()
    except Exception:
        return None

def get_date_info(path, ext):
    """Extract original capture date (EXIF) or file creation date."""
    if ext in {'.jpg', '.jpeg', '.tiff'}:
        try:
            image = Image.open(path)
            info = image._getexif()
            if info:
                for tag, value in info.items():
                    if TAGS.get(tag) == "DateTimeOriginal":
                        return value
        except Exception:
            pass
    
    # Fallback to creation time for videos or images without EXIF
    try:
        ctime = os.path.getctime(path)
        return datetime.fromtimestamp(ctime).strftime('%Y:%m:%d %H:%M:%S')
    except Exception:
        return "Unknown"

def run_auto_backup():
    files_dict = {}
    all_records = []
    move_queue = []
    total_moved_size = 0

    print(f">>> Starting duplicate cleanup. Target: {TARGET_DRIVE}")
    print(f">>> Duplicates will be moved to: {BACKUP_DIR}")
    print("-" * 70)

    # 1. Scanning Files
    for root, _, files in os.walk(TARGET_DRIVE):
        # Prevent infinite loop by skipping the backup directory
        if os.path.abspath(root).startswith(os.path.abspath(BACKUP_DIR)):
            continue

        for file in files:
            ext = Path(file).suffix.lower()
            if ext in EXTENSIONS:
                path = os.path.join(root, file)
                
                # Real-time status update
                print(f" Scanning: {path[:70]}...", end='\r')
                
                f_hash = get_file_hash(path)
                if not f_hash: continue
                
                mtime = os.path.getmtime(path)
                info = {
                    'title': file,
                    'size': os.path.getsize(path),
                    'date_taken': get_date_info(path, ext),
                    'date_mod': datetime.fromtimestamp(mtime).strftime('%Y:%m:%d %H:%M:%S'),
                    'path': path,
                    'mtime': mtime,
                    'status': 'Keep'
                }
                files_dict.setdefault(f_hash, []).append(info)

    print("\n" + "-" * 70)
    print(">>> Scan complete. Processing duplicates and generating logs...")

    # 2. Duplicate Detection and Execution
    with open(LOG_FILE, 'w', newline='', encoding='utf-8-sig') as f:
        keys = ['status', 'title', 'size', 'date_taken', 'date_mod', 'path']
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()

        for f_hash, info_list in files_dict.items():
            if len(info_list) > 1:
                # Sort rules:
                # 1. Keep files NOT in Google Photos (Move Google Photos first)
                # 2. Keep longer filenames (Move shorter filenames)
                # Key returns (is_not_google, name_length). True/High values are kept (index 0).
                info_list.sort(key=lambda x: (not ('Google Photos' in x['path'] or 'Google 포토' in x['path']), len(x['title'])), reverse=True)
                
                for i, item in enumerate(info_list):
                    if i > 0: # Move older duplicates (index 1 and beyond)
                        item['status'] = 'Move to Backup'
                        
                        # Calculate relative path to preserve directory structure
                        rel_path = os.path.relpath(item['path'], TARGET_DRIVE)
                        dest_path = os.path.join(BACKUP_DIR, rel_path)
                        
                        try:
                            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                            shutil.move(item['path'], dest_path)
                            total_moved_size += item['size']
                            move_queue.append(item)
                        except Exception as e:
                            print(f"\n[Error] Failed to move: {item['path']} -> {e}")
                    
                    # Record all file info (both Keep and Move) to CSV
                    writer.writerow({k: item[k] for k in keys})

    # 3. Final Summary
    print("-" * 70)
    print("Task Completed Successfully!")
    print(f"- Total files moved: {len(move_queue)}")
    print(f"- Total disk space cleared: {total_moved_size / (1024*1024):.2f} MB")
    print(f"- Detailed log saved to: {os.path.abspath(LOG_FILE)}")
    print(f"- Backup directory: {BACKUP_DIR}")
    print("-" * 70)

if __name__ == "__main__":
    run_auto_backup()