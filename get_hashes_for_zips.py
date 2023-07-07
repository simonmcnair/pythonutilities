import os
import zipfile
import rarfile
import tarfile
import hashlib
import csv
import shutil
import py7zr
import msilib
from datetime import datetime
import tempfile


def process_archive(file_path, log_writer):
    try:
        archive_name = os.path.basename(file_path)
        archive_dir = os.path.dirname(file_path)
        archive_type = ''
        if zipfile.is_zipfile(file_path):
            archive_type = 'ZIP'
            archive = zipfile.ZipFile(file_path, 'r')
        elif rarfile.is_rarfile(file_path):
            archive_type = 'RAR'
            archive = rarfile.RarFile(file_path, 'r')
        elif file_path.endswith('.tar'):
            archive_type = 'TAR'
            archive = tarfile.open(file_path, 'r')
        elif file_path.endswith('.7z'):
            archive_type = '7Z'
            archive = py7zr.SevenZipFile(file_path, 'r')
        elif file_path.endswith('.msi'):
            archive_type = 'MSI'
            archive = msilib.OpenDatabase(file_path, msilib.MSIDBOPEN_READONLY)
        else:
            return
        
        # Extract files to a temporary directory
        temp_dir = tempfile.mkdtemp()
        archive.extractall(temp_dir)
        
        # Process extracted files
        for root, dirs, files in os.walk(temp_dir):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                with open(file_path, 'rb') as f:
                    file_bytes = f.read()
                file_checksum = hashlib.sha1(file_bytes).hexdigest()
                log_writer.writerow([datetime.now(), archive_dir, archive_name, file_path, os.path.basename(file_name), file_checksum])
        
        archive.close()
        
        # Delete temporary directory
        shutil.rmtree(temp_dir)
        
    except Exception as e:
        print(f"Error processing archive {file_path}: {e}")
        shutil.move(file_path, os.path.join(archive_dir, 'badarchives'))


def process_directory(directory_path, log_file_path):
    with open(log_file_path, 'a', newline='') as log_file:
        log_writer = csv.writer(log_file)
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                process_archive(file_path, log_writer)


if __name__ == '__main__':
    directory_path = input("Enter directory path: ")
    log_file_path = input("Enter log file path: ")
    if not os.path.isdir(directory_path):
        print(f"{directory_path} is not a valid directory.")
    else:
        process_directory(directory_path, log_file_path)
