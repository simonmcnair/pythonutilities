import os
import zipfile
import rarfile
import tarfile
import hashlib
import csv
import shutil

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
        
        for file_info in archive.infolist():
            if not file_info.is_dir():
                file_name = file_info.filename
                file_bytes = archive.read(file_name)
                file_checksum = hashlib.sha1(file_bytes).hexdigest()
                file_path = os.path.join(archive_dir, file_name)
                log_writer.writerow([archive_dir, archive_name, file_path, os.path.basename(file_name), file_checksum])
        
        archive.close()
        
        # delete extracted files
        if archive_type in ['ZIP', 'RAR', '7Z']:
            shutil.rmtree(os.path.join(archive_dir, archive_name + '_extracted'))
        elif archive_type == 'TAR':
            for member in archive.getmembers():
                if member.isreg():
                    os.remove(os.path.join(archive_dir, member.name))
        elif archive_type == 'MSI':
            pass  # do nothing since MSI files don't extract to a directory
    except Exception as e:
        print(f"Error processing archive {file_path}: {e}")
        shutil.move(file_path, os.path.join(archive_dir, 'badarchives'))

def scan_directory(directory_path, log_path):
    with open(log_path, 'w', newline='') as log_file:
        log_writer = csv.writer(log_file)
        log_writer.writerow(['Timestamp', 'Archive Path', 'Archive Name', 'File Path', 'File Name', 'Checksum'])
        
        for root in os.listdir(directory_path):
            full_path = os.path.join(directory_path, root)
            if os.path.isdir(full_path):
                for root2, dirs, files in os.walk(full_path):
                    for file_name in files:
                        file_path = os.path.join(root2, file_name)
                        if zipfile.is_zipfile(file_path) or rarfile.is_rarfile(file_path) or file_name.endswith('.tar') or file_name.endswith('.7z') or file_name.endswith('.msi'):
                            process_archive(file_path, log_writer)

# Test the program
directory_path = '/srv/mergerfs/data/Software/sort2/ZIP/'
log_path = '/srv/mergerfs/data/Software/sort2/ZIP/logfile.txt'

scan_directory(directory_path, log_path)
