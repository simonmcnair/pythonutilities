import hashlib
import os
import zipfile
import tarfile
import rarfile
import py7zr
import csv
from datetime import datetime

# Function to calculate the SHA1 checksum of a file
def sha1_checksum(file_path):
    with open(file_path, 'rb') as f:
        checksum = hashlib.sha1()
        while True:
            data = f.read(8192)
            if not data:
                break
            checksum.update(data)
    return checksum.hexdigest()

# Function to generate SHA1 checksums for all files inside an archive
def process_archive(file_path, log_writer):
    archive_type = os.path.splitext(file_path)[1]
    archive_name = os.path.basename(file_path)
    
    try:
        if archive_type == '.zip':
            with zipfile.ZipFile(file_path, 'r') as zip_archive:
                for member in zip_archive.infolist():
                    if not member.is_dir():
                        file_name = os.path.basename(member.filename)
                        checksum = sha1_checksum(zip_archive.extract(member))
                        log_writer.writerow([datetime.now(), file_path, archive_name, member.filename, file_name, checksum])
    
        elif archive_type == '.msi':
            with zipfile.ZipFile(file_path, 'r') as msi_archive:
                for member in msi_archive.infolist():
                    if not member.is_dir() and member.filename.endswith('.cab'):
                        with msi_archive.open(member) as cab_file:
                            with py7zr.SevenZipFile(cab_file, mode='r') as cab_archive:
                                for name in cab_archive.getnames():
                                    if not cab_archive.getinfo(name).is_dir():
                                        file_name = os.path.basename(name)
                                        checksum = sha1_checksum(cab_archive.extract(name))
                                        log_writer.writerow([datetime.now(), file_path, archive_name, member.filename, file_name, checksum])
    
        elif archive_type == '.tar':
            with tarfile.open(file_path, 'r') as tar_archive:
                for member in tar_archive.getmembers():
                    if not member.isdir():
                        file_name = os.path.basename(member.name)
                        checksum = sha1_checksum(tar_archive.extractfile(member).name)
                        log_writer.writerow([datetime.now(), file_path, archive_name, member.name, file_name, checksum])
    
        elif archive_type == '.rar':
            with rarfile.RarFile(file_path, 'r') as rar_archive:
                for member in rar_archive.infolist():
                    if not member.isdir():
                        file_name = os.path.basename(member.filename)
                        checksum = sha1_checksum(rar_archive.extract(member).name)
                        log_writer.writerow([datetime.now(), file_path, archive_name, member.filename, file_name, checksum])
    
        elif archive_type == '.7z':
            with py7zr.SevenZipFile(file_path, mode='r') as seven_zip_archive:
                for name in seven_zip_archive.getnames():
                    if not seven_zip_archive.getinfo(name).is_dir():
                        file_name = os.path.basename(name)
                        checksum = sha1_checksum(seven_zip_archive.extract(name))
                        log_writer.writerow([datetime.now(), file_path, archive_name, name, file_name, checksum])
    except:
        print(f"Corrupt archive: {file_path}")
        bad_archives_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'badarchives')
        os.makedirs(bad_archives_dir, exist_ok=True)
        os.replace(file_path, os.path.join(bad_archives_dir, os.path.basename(file_path)))

# Function to scan a directory recursively and process all archives inside
def scan_directory(directory_path, log_path):
    with open(log_path, 'w', newline='') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(['Timestamp', 'Archive Path', 'Archive Name', 'File Path', 'File Name', 'Checksum'])
        
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if zipfile.is_zipfile(file_path) or rarfile.is_rarfile(file_path) or file_name.endswith('.tar') or file_name.endswith('.7z') or file_name.endswith('.msi'):
                    process_archive(file_path, log_writer)

# Test the program
directory_path = '/srv/mergerfs/data/Software/sort2/ZIP'
log_path = '/srv/mergerfs/data/Software/sort2/ZIP/logfile.txt'
scan_directory(directory_path, log_path)
