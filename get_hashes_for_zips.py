import hashlib
import os
import csv
import zipfile
import tarfile
import rarfile
import libarchive.public as public
from msilib import SummaryInformation

def get_file_checksum(file_path, algorithm="sha1", block_size=65536):
    """
    Calculate the checksum of a file using the given algorithm.
    """
    hash_algo = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while True:
            data = f.read(block_size)
            if not data:
                break
            hash_algo.update(data)
    return hash_algo.hexdigest()

def process_archive(archive_path, log_file):
    """
    Process an archive and write its checksums to the log file.
    """
    archive_name = os.path.basename(archive_path)
    archive_type = os.path.splitext(archive_path)[1].lower()
    try:
        if archive_type == ".zip":
            archive = zipfile.ZipFile(archive_path)
        elif archive_type == ".tar":
            archive = tarfile.TarFile(archive_path)
        elif archive_type == ".rar":
            archive = rarfile.RarFile(archive_path)
        else:
            archive = public.file_reader(archive_path, "7zip")
        
        for member in archive.getmembers():
            if member.isfile():
                member_path = os.path.join(archive_path, member.name)
                checksum = get_file_checksum(member_path)
                log_file.writerow([os.path.abspath(member_path), archive_name, checksum])
    except Exception as e:
        print(f"Error processing {archive_path}: {e}")
        bad_archive_path = os.path.join(os.path.dirname(archive_path), "badarchives", os.path.basename(archive_path))
        os.rename(archive_path, bad_archive_path)
        

def process_directory(directory_path):
    """
    Recursively process all archives in the given directory.
    """
    with open("log.csv", "w", newline="") as f:
        log_file = csv.writer(f)
        log_file.writerow(["File Path", "Archive Name", "Checksum"])
        for root, dirs, files in os.walk(directory_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                if os.path.splitext(file_name)[1].lower() in [".zip", ".tar", ".rar", ".7z"]:
                    process_archive(file_path, log_file)

if __name__ == "__main__":
    directory_path = input("Enter directory path: ")
    process_directory(directory_path)
