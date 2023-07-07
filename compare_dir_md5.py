import os
import json
import hashlib
import csv

def generate_hash(filepath):
    """
    Generates SHA256 hash for a given file.
    """
    hash_object = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)  # Read file in chunks of 64KB
            if not data:
                break
            hash_object.update(data)
    return hash_object.hexdigest()


def get_file_paths(directory):
    """
    Returns a list of file paths in a directory and its subdirectories recursively.
    """
    file_paths = []
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            file_paths.append(os.path.join(dirpath, filename))
    return file_paths


def read_cache_json(cache_file):
    """
    Reads cache data from a JSON file and returns it as a dictionary.
    """
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            return json.load(f)
    else:
        return {}


def write_cache_json(cache_file, data):
    """
    Writes cache data to a JSON file.
    """
    with open(cache_file, 'w') as f:
        json.dump(data, f, indent=4)


def process_files(dir1, dir2, cache_file, unique_csv, duplicate_csv):
    """
    Processes files in two directories, generates SHA256 hashes,
    writes to CSV files, and updates the cache.
    """
    file_paths = get_file_paths(dir1) + get_file_paths(dir2)
    cache_data = read_cache_json(cache_file)
    unique_hashes = set()
    duplicate_hashes = set()

    for file_path in file_paths:
        if file_path in cache_data:
            hash_value = cache_data[file_path]
            if hash_value in unique_hashes:
                duplicate_hashes.add(hash_value)
                print(f"Duplicate hash found: Hash - {hash_value}, File - {file_path}")
            else:
                unique_hashes.add(hash_value)
        else:
            hash_value = generate_hash(file_path)
            cache_data[file_path] = hash_value
            unique_hashes.add(hash_value)
            print(f"New hash generated: Hash - {hash_value}, File - {file_path}")

    with open(unique_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hash', 'Filepath'])
        for hash_value in unique_hashes:
            for file_path, value in cache_data.items():
                if value == hash_value:
                    writer.writerow([hash_value, file_path])

    with open(duplicate_csv, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hash', 'Filepath'])
        for hash_value in duplicate_hashes:
            for file_path, value in cache_data.items():
                if value == hash_value:
                    writer.writerow([hash_value, file_path])

    write_cache_json(cache_file, cache_data)
    print("Unique hashes written to unique.csv")
    print("Duplicate hashes written to duplicate.csv")


if __name__ == "__main__":
    dir1 = "/path/to/directory1"
    dir2 = "/path/to/directory2"
    cache_file = "cache.json"
    unique_csv = "unique.csv"
    duplicate_csv = "duplicate.csv"

    process_files(dir1, dir2, cache_file, unique_csv, duplicate_csv)
