import os
import csv
import hashlib
import shutil
import zipfile
import tarfile
import rarfile
import py7zr
import msilib


def process_archive(file_path, log_writer):
    archive_dir, archive_name = os.path.split(file_path)
    archive_type = archive_name.split('.')[-1].lower()
    try:
        if archive_type == 'zip':
            with zipfile.ZipFile(file_path, 'r') as zip_file:
                for zip_info in zip_file.infolist():
                    with zip_file.open(zip_info) as file:
                        sha1 = hashlib.sha1(file.read()).hexdigest()
                        log_writer.writerow([get_timestamp(), archive_dir, archive_name, zip_info.filename, os.path.basename(zip_info.filename), sha1])
        elif archive_type == 'msi':
            db = msilib.OpenDatabase(file_path, msilib.MSIDBOPEN_READONLY)
            view = db.OpenView("SELECT * FROM _Streams")
            view.Execute(None)
            while True:
                rec = view.Fetch()
                if rec is None:
                    break
                stream_name = rec.GetString(1)
                if stream_name.startswith("#"):
                    continue
                with db.OpenStream(stream_name) as file:
                    sha1 = hashlib.sha1(file.read()).hexdigest()
                    log_writer.writerow([get_timestamp(), archive_dir, archive_name, stream_name, os.path.basename(stream_name), sha1])
        elif archive_type == 'tar':
            with tarfile.open(file_path, 'r') as tar_file:
                for tar_info in tar_file.getmembers():
                    if tar_info.isfile():
                        with tar_file.extractfile(tar_info) as file:
                            sha1 = hashlib.sha1(file.read()).hexdigest()
                            log_writer.writerow([get_timestamp(), archive_dir, archive_name, tar_info.name, os.path.basename(tar_info.name), sha1])
        elif archive_type == 'rar':
            with rarfile.RarFile(file_path, 'r') as rar_file:
                for rar_info in rar_file.infolist():
                    if rar_info.isfile():
                        with rar_file.open(rar_info) as file:
                            sha1 = hashlib.sha1(file.read()).hexdigest()
                            log_writer.writerow([get_timestamp(), archive_dir, archive_name, rar_info.filename, os.path.basename(rar_info.filename), sha1])
        elif archive_type == '7z':
            with py7zr.SevenZipFile(file_path, mode='r') as seven_zip:
                for file_info in seven_zip.getnames():
                    with seven_zip.open(file_info) as file:
                        sha1 = hashlib.sha1(file.read()).hexdigest()
                        log_writer.writerow([get_timestamp(), archive_dir, archive_name, file_info, os.path.basename(file_info), sha1])
        else:
            print(f"Unsupported archive type: {archive_type}")
    except Exception as e:
        print(f"Error processing archive {file_path}: {e}")
        shutil.move(file_path, os.path.join(os.path.dirname(file_path), 'badarchives', os.path.basename(file_path)))


def process_directory(directory_path):
    log_file_path = os.path.join(directory_path, 'checksum_log.csv')
    with open(log_file_path, 'w', newline='') as log_file:
        log_writer = csv.writer(log_file)
        log_writer
