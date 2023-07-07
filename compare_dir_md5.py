import os
import hashlib
import json
import csv

# Function to generate SHA256 hash
def generate_hash(file_path):
    with open(file_path, 'rb') as f:
        data = f.read()
        hash_object = hashlib.sha256()
        hash_object.update(data)
        return hash_object.hexdigest()

# Function to recursively get file paths in a directory
def get_file_paths(directory):
    file_paths = []
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_paths.append(file_path)
    return file_paths

# Function to read cache.json file
def read_cache_json(cache_file):
    cache_data = {}
    if os.path.isfile(cache_file):
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
    return cache_data

# Function to write to cache.json file
def write_cache_json(cache_file, cache_data):
    with open(cache_file, 'w') as f:
        json.dump(cache_data, f)

# Function to process file paths and generate hashes
def process_files(dir1, dir2, cache_file, unique_csv_file, duplicate_csv_file):
    file_paths = get_file_paths(dir1) + get_file_paths(dir2)
    cache_data = read_cache_json(cache_file)
    hash_map = {}
    duplicate_hashes = set()
    unique_hashes = set()
    for file_path in file_paths:
        file_hash = generate_hash(file_path)
        if file_hash in hash_map:
            duplicate_hashes.add(file_hash)
            hash_map[file_hash].append(file_path)
        else:
            hash_map[file_hash] = [file_path]
            unique_hashes.add(file_hash)

    # Write duplicate hashes to duplicate.csv
    with open(duplicate_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hash', 'Filepath'])
        for duplicate_hash in duplicate_hashes:
            file_paths = hash_map[duplicate_hash]
            writer.writerow([duplicate_hash] + file_paths)

    # Write unique hashes to unique.csv
    with open(unique_csv_file, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hash', 'Filepath'])
        for unique_hash in unique_hashes:
            file_path = hash_map[unique_hash][0]
            writer.writerow([unique_hash, file_path])

    # Update cache.json with new hash data
    cache_data.update(hash_map)
    write_cache_json(cache_file, cache_data)

    # Print duplicate hashes and corresponding filepaths
    print("Duplicate Hashes:")
    for duplicate_hash in duplicate_hashes:
        file_paths = hash_map[duplicate_hash]
        print("Hash: {}".format(duplicate_hash))
        print("Filepaths:")
        for file_path in file_paths:
            print(file_path)

# Main program
if __name__ == '__main__':
    dir1 = 'directory1'  # Replace with the path to the first directory
    dir2 = 'directory2'  # Replace with the path to the second directory
    cache_file = 'cache.json'  # Replace with the desired cache file name
    unique_csv_file = 'unique.csv'  # Replace with the desired unique hashes CSV file name
    duplicate_csv_file = 'duplicate.csv'  # Replace with the desired duplicate hashes CSV file name

    process_files(dir1, dir2, cache_file, unique_csv_file, duplicate_csv_file)
