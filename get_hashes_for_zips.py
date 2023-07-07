import os
import csv
import hashlib
import shutil
import threading
from multiprocessing import Pool

def compute_checksums(file_path):
    try:
        with open(file_path, 'rb') as f:
            hasher = hashlib.sha256()
            buf = f.read(65536)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(65536)
            return hasher.hexdigest()
    except Exception as e:
        print(f"Failed to compute checksum for {file_path}: {e}")
        return None

def extract_archive(archive_path, dest_dir):
    try:
        shutil.unpack_archive(archive_path, dest_dir)
        print(f"Extracted {archive_path}")
    except Exception as e:
        print(f"Failed to extract {archive_path}: {e}")
        os.rename(archive_path, os.path.join(os.path.dirname(archive_path), "badarchives", os.path.basename(archive_path)))

def process_archive(root_dir, archive_path, log_file):
    archive_name = os.path.basename(archive_path)
    dest_dir = os.path.join(root_dir, os.path.splitext(archive_name)[0])
    os.makedirs(dest_dir, exist_ok=True)
    extract_archive(archive_path, dest_dir)
    for dirpath, dirnames, filenames in os.walk(dest_dir):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            checksum = compute_checksums(file_path)
            if checksum is not None:
                log_file.writerow([file_path, archive_name, checksum])
    shutil.rmtree(dest_dir)

def process_archives_in_dir(root_dir):
    with open(os.path.join(root_dir, "checksums.csv"), 'w', newline='') as f:
        log_file = csv.writer(f)
        log_file.writerow(["File Path", "Archive Name", "SHA-256 Checksum"])
        archives = [os.path.join(root, file) for root, dirs, files in os.walk(root_dir) for file in files if os.path.splitext(file)[1] in ['.zip', '.msi', '.tar', '.rar', '.7z']]
        pool = Pool()
        for archive_path in archives:
            pool.apply_async(process_archive, (root_dir, archive_path, log_file))
        pool.close()
        pool.join()

if __name__ == '__main__':
    root_dir = input("Enter the directory path to scan: ")
    if not os.path.isdir(root_dir):
        print("Invalid directory path.")
    else:
        process_archives_in_dir(root_dir)
