import os
import hashlib
import json
import csv

def scan_directory(directory):
    """
    Recursively scan a directory and return a list of file paths.
    """
    file_paths = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_paths.append(file_path)
    return file_paths

def generate_hash(file_path, chunk_size=1):
    """
    Generate a SHA256 hash for a file.
    """
    print(f"Generating hash for file: {file_path}")
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as file:
        while True:
            data = file.read(chunk_size * 1024 * 1024)  # Read chunk_size MB at a time
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def create_json_cache(file_hashes):
    """
    Create a JSON cache file with file hashes.
    """
    with open('cache.json', 'w') as cache_file:
        json.dump(file_hashes, cache_file, indent=4)

def update_json_cache(file_hashes):
    """
    Update an existing JSON cache file with file hashes.
    """
    with open('cache.json', 'r') as cache_file:
        existing_hashes = json.load(cache_file)
    existing_hashes.update(file_hashes)
    with open('cache.json', 'w') as cache_file:
        json.dump(existing_hashes, cache_file, indent=4)

def create_csv_file(file_hashes, output_file):
    """
    Create a CSV file with file hashes.
    """
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Hash', 'File Path'])
        for file_path, file_hash in file_hashes.items():
            writer.writerow([file_hash, file_path])

def process_files(dir1, dir2, chunk_size):
    """
    Process files in dir1 and dir2, generate hashes, and create JSON cache and CSV files.
    """
    file_hashes = {}
    file_paths = scan_directory(dir1) + scan_directory(dir2)
    for file_path in file_paths:
        file_hash = generate_hash(file_path, chunk_size)
        if file_hash not in file_hashes:
            file_hashes[file_hash] = file_path
        else:
            print(f"Duplicate hash found: {file_hash}")
            print(f"File Path: {file_path}")
            print(f"File Path with same hash: {file_hashes[file_hash]}")
            print("------")
    if not os.path.exists('cache.json'):
        create_json_cache(file_hashes)
    else:
        update_json_cache(file_hashes)
    create_csv_file(file_hashes, 'unique_hashes.csv')
