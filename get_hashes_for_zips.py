import os
import sys
import hashlib
import csv
import threading

# function to calculate SHA-1 hash of a file
def calculate_hash(file_path):
    sha1_hash = hashlib.sha1()
    with open(file_path, "rb") as f:
        while True:
            data = f.read(1024)
            if not data:
                break
            sha1_hash.update(data)
    return sha1_hash.hexdigest()

# function to process a single archive file
def process_archive(archive_path, log_file):
    try:
        with open(archive_path, "rb") as f:
            magic_number = f.read(2)
            f.seek(0)
            if magic_number == b"PK":
                # zip archive
                import zipfile
                with zipfile.ZipFile(archive_path) as zip_file:
                    for member in zip_file.infolist():
                        file_hash = calculate_hash(zip_file.extract(member))
                        log_file.writerow([os.path.abspath(member.filename), archive_path, file_hash])
            elif magic_number == b"Rar":
                # rar archive
                import rarfile
                with rarfile.RarFile(archive_path) as rar_file:
                    for member in rar_file.infolist():
                        file_hash = calculate_hash(rar_file.extract(member))
                        log_file.writerow([os.path.abspath(member.filename), archive_path, file_hash])
            elif magic_number == b"\x1f\x8b":
                # gzip archive
                import tarfile
                with tarfile.open(archive_path, "r:gz") as tar_file:
                    for member in tar_file.getmembers():
                        file_hash = calculate_hash(tar_file.extractfile(member))
                        log_file.writerow([os.path.abspath(member.name), archive_path, file_hash])
            elif magic_number == b"BZ":
                # bzip2 archive
                import tarfile
                with tarfile.open(archive_path, "r:bz2") as tar_file:
                    for member in tar_file.getmembers():
                        file_hash = calculate_hash(tar_file.extractfile(member))
                        log_file.writerow([os.path.abspath(member.name), archive_path, file_hash])
            elif magic_number == b"7z":
                # 7zip archive
                import py7zr
                with py7zr.SevenZipFile(archive_path, "r") as zip_file:
                    for member in zip_file.getnames():
                        file_hash = calculate_hash(zip_file.extract(member))
                        log_file.writerow([os.path.abspath(member), archive_path, file_hash])
            elif magic_number == b"\xD0\xCF":
                # Microsoft Office Document
                import msilib
                with msilib.CAB(archive_path) as cab_file:
                    for member in cab_file.getmembers():
                        file_hash = calculate_hash(cab_file.extract(member))
                        log_file.writerow([os.path.abspath(member.name), archive_path, file_hash])
            else:
                print(f"Unknown file type: {archive_path}")
    except Exception as e:
        print(f"Error processing archive {archive_path}: {e}")
        os.makedirs("badarchives", exist_ok=True)
        os.rename(archive_path, os.path.join("badarchives", os.path.basename(archive_path)))

# function to process all archives in a directory
def process_directory(directory):
    log_filename = os.path.join(directory, "archive_checksums.csv")
    with open(log_filename, "w", newline="") as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(["File path", "Archive path", "SHA-1 hash"])
        for root, _, filenames
