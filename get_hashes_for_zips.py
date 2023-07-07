import os
import sys
import hashlib
import csv
import threading
import queue
import logging
import traceback
import shutil
import zipfile
import tarfile
import rarfile
import lzma
import argparse

logging.basicConfig(level=logging.INFO, filename='archive_processing.log', filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')

ARCHIVE_FORMATS = ['.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.rar', '.7z', '.msi', '.msm', '.msp', '.msu']
BAD_ARCHIVES_DIR = 'bad_archives'

class ArchiveProcessor:
    def __init__(self, queue, output_file):
        self.queue = queue
        self.output_file = output_file

    def run(self):
        while True:
            try:
                archive_file = self.queue.get(timeout=1)
                self.process_archive(archive_file)
                self.queue.task_done()
            except queue.Empty:
                break
            except Exception as e:
                logging.error(f"Error processing archive: {archive_file}")
                logging.error(traceback.format_exc())

    def process_archive(self, archive_file):
        try:
            archive_name = os.path.basename(archive_file)
            logging.info(f"Processing archive: {archive_name}")
            sha1_dict = {}

            # extract archive
            with self.extract_archive(archive_file) as extract_dir:
                # calculate sha1 checksum for each file in the archive
                for root, dirs, files in os.walk(extract_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        with open(file_path, 'rb') as f:
                            sha1 = hashlib.sha1(f.read()).hexdigest()
                            sha1_dict[file_path] = sha1

            # write results to output file
            with open(self.output_file, mode='a', newline='') as output_csv:
                writer = csv.writer(output_csv)
                for file_path, sha1 in sha1_dict.items():
                    writer.writerow([archive_file, file_path, sha1])
        except Exception as e:
            logging.error(f"Error processing archive: {archive_file}")
            logging.error(traceback.format_exc())

    def extract_archive(self, archive_file):
        try:
            if not os.path.exists(BAD_ARCHIVES_DIR):
                os.makedirs(BAD_ARCHIVES_DIR)

            # create a temporary directory to extract archive
            extract_dir = os.path.join(os.path.dirname(archive_file), '__extracted__')
            os.makedirs(extract_dir, exist_ok=True)

            # extract archive
            archive_name, ext = os.path.splitext(archive_file)
            if ext == '.zip':
                with zipfile.ZipFile(archive_file, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
            elif ext in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']:
                with tarfile.open(archive_file, 'r:*') as tar_ref:
                    tar_ref.extractall(extract_dir)
            elif ext == '.rar':
                with rarfile.RarFile(archive_file, 'r') as rar_ref:
                    rar_ref.extractall(extract_dir)
            elif ext == '.7z':
                with lzma.open(archive_file) as file_ref:
                    with open(os.path.join(extract_dir, '__temp.7z'), 'wb') as temp_file:
                        shutil.copyfileobj(file_ref,
