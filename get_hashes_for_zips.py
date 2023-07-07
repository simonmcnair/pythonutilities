import os
import hashlib
import csv
import argparse
import multiprocessing
from tqdm import tqdm
import zipfile
import tarfile
import rarfile
import py7zr
import msilib

ARCHIVE_TYPES = {
    '.zip': zipfile.ZipFile,
    '.tar': tarfile.TarFile,
    '.gz': tarfile.TarFile,
    '.bz2': tarfile.TarFile,
    '.xz': tarfile.TarFile,
    '.rar': rarfile.RarFile,
    '.7z': py7zr.SevenZipFile,
    '.msi': msilib.OpenDatabase
}

def compute_sha1(file_path):
    with open(file_path, 'rb') as f:
        content = f.read()
    sha1 = hashlib.sha1(content).hexdigest()
    return sha1

def process_archive(archive_path, output_file):
    archive_type = os.path.splitext(archive_path)[1].lower()
    if archive_type not in ARCHIVE_TYPES:
        return
    
    try:
        archive = ARCHIVE_TYPES[archive_type](archive_path, 'r')
    except Exception as e:
        print(f"Error opening archive {archive_path}: {e}")
        return
    
    try:
        for file_info in archive.infolist():
            file_name = file_info.filename
            if file_name.startswith('__MACOSX'):
                continue
            if file_info.is_dir():
                continue
            if not file_name:
                continue
            content = archive.read(file_info)
            sha1 = hashlib.sha1(content).hexdigest()
            output_file.writerow([archive_path, file_name, sha1])
    except Exception as e:
        print(f"Error processing archive {archive_path}: {e}")
    finally:
        archive.close()

def process_directory(directory_path, output_file):
    for root, dirs, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            process_archive(file_path, output_file)

def main():
    parser = argparse.ArgumentParser(description='Generate SHA1 checksums of files inside archives.')
    parser.add_argument('directory', metavar='directory', type=str, help='the directory to scan for archives')
    parser.add_argument('output_file', metavar='output_file', type=str, help='the output CSV file')
    parser.add_argument('--num-workers', dest='num_workers', type=int, default=multiprocessing.cpu_count(), help='the number of worker processes to use (default: number of CPUs)')
    args = parser.parse_args()
    
    with open(args.output_file, 'w', newline='') as f:
        output_file = csv.writer(f)
        output_file.writerow(['Archive Path', 'File Path', 'SHA1'])
        
        archives = [os.path.join(root, file_name) for root, dirs, files in os.walk(args.directory) for file_name in files if os.path.splitext(file_name)[1].lower() in ARCHIVE_TYPES]
        
        with multiprocessing.Pool(args.num_workers) as pool, tqdm(total=len(archives)) as progress_bar:
            for _ in pool.imap_unordered(process_archive, [(archive_path, output_file) for archive_path in archives]):
                progress_bar.update()
        
if __name__ == '__main__':
    main()
