import os
import json
import hashlib
import csv

def create_file_list(directory1, directory2):
    """
    Creates an array containing the filepaths of all files recursively
    contained in two directories, sorted by filename.

    Args:
        directory1 (str): Path to the first directory.
        directory2 (str): Path to the second directory.

    Returns:
        list: An array of filepaths sorted by filename.
    """
    file_list = []
    for directory in [directory1, directory2]:
        for dirpath, dirnames, filenames in os.walk(directory):
            for filename in filenames:
                file_list.append(os.path.join(dirpath, filename))
    return sorted(file_list, key=lambda x: os.path.basename(x))

def generate_hash(filepath):
    """
    Generates the SHA256 hash of a file.

    Args:
        filepath (str): Path to the file.

    Returns:
        str: The hexadecimal representation of the SHA256 hash.
    """
    with open(filepath, 'rb') as f:
        data = f.read()
    sha256_hash = hashlib.sha256()
    sha256_hash.update(data)
    return sha256_hash.hexdigest()

def process_files(file_list):
    """
    Processes the list of files and identifies duplicate filenames.
    Writes the filepath and SHA256 hash of duplicates to cache.json
    and prints them to the screen.

    Args:
        file_list (list): An array of filepaths sorted by filename.
    """
    unique_hashes = {}
    duplicate_hashes = {}
    for filepath in file_list:
        filename = os.path.basename(filepath)
        file_hash = generate_hash(filepath)
        if file_hash in unique_hashes:
            print(f"Duplicate found: {filename} - {filepath}")
            duplicate_hashes[file_hash] = duplicate_hashes.get(file_hash, []) + [filepath]
        else:
            unique_hashes[file_hash] = filepath

    with open('cache.json', 'w') as f:
        json.dump(duplicate_hashes, f, indent=4)

def update_cache():
    """
    Reads the cache.json file and generates hashes for files without a hash.
    """
    if os.path.exists('cache.json'):
        with open('cache.json', 'r') as f:
            duplicate_hashes = json.load(f)
        for file_hash, filepaths in duplicate_hashes.items():
            for filepath in filepaths:
                if not os.path.exists(filepath):
                    continue
                if file_hash not in unique_hashes:
                    unique_hashes[file_hash] = filepath

def write_csv():
    """
    Writes the unique and duplicate hashes with their filepaths to CSV files.
    """
    with open('unique_hashes.csv', 'w') as f1, open('duplicate_hashes.csv', 'w') as f2:
        writer1 = csv.writer(f1)
        writer2 = csv.writer(f2)
        writer1.writerow(['Hash', 'Filepath'])
        writer2.writerow(['Hash', 'Filepath'])
        for file_hash, filepath in unique_hashes.items():
            writer1.writerow([file_hash, filepath])
        for file_hash, filepaths in duplicate_hashes.items():
            for filepath in filepaths:
                writer2.writerow([file_hash, filepath])

if __name__ == '__main__':
    directory1 = 'directory1_path'
    directory2 = 'directory2_path'
    file_list = create_file_list(directory1, directory2)
    update_cache()
    process_files(file_list)
    write_csv()
