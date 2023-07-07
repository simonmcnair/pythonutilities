import os
import hashlib
import json
import csv

# Function to calculate SHA256 hash of a file
def get_file_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(8192)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

# Function to create an array of filepaths from two directories recursively
def create_filepaths_array(dir1, dir2):
    filepaths = []
    for dir_path in (dir1, dir2):
        for dirpath, _, filenames in os.walk(dir_path):
            for filename in filenames:
                filepaths.append(os.path.join(dirpath, filename))
    filepaths.sort(key=lambda x: os.path.basename(x))  # Sort by filename
    return filepaths

# Function to write filepaths and hashes to cache.json
def write_to_cache(filepaths, cache):
    for filepath in filepaths:
        if filepath not in cache:
            hash_value = get_file_hash(filepath)
            cache[filepath] = hash_value
    with open('cache.json', 'w') as f:
        json.dump(cache, f, indent=4)

# Function to read cache.json and get files without hash
def get_files_without_hash(cache):
    files_without_hash = []
    for filepath, hash_value in cache.items():
        if not hash_value:
            files_without_hash.append(filepath)
    return files_without_hash

# Function to write unique hashes and duplicate hashes to CSV files
def write_to_csv(unique_hashes, duplicate_hashes):
    with open('unique.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Filepath', 'Hash'])
        for filepath, hash_value in unique_hashes.items():
            writer.writerow([filepath, hash_value])
    with open('dupehashes.csv', 'w') as f:
        writer = csv.writer(f)
        writer.writerow(['Filepath', 'Hash'])
        for filepath, hash_value in duplicate_hashes.items():
            writer.writerow([filepath, hash_value])

# Main procedure
def main(dir1, dir2):
    # Read cache.json
    try:
        with open('cache.json', 'r') as f:
            cache = json.load(f)
    except FileNotFoundError:
        cache = {}

    # Create filepaths array
    filepaths = create_filepaths_array(dir1, dir2)

    # Write filepaths and hashes to cache.json
    write_to_cache(filepaths, cache)

    # Get files without hash
    files_without_hash = get_files_without_hash(cache)

    # Print duplicate filenames
    duplicate_filenames = set()
    for filepath in filepaths:
        filename = os.path.basename(filepath)
        if filename in duplicate_filenames:
            print(f'Duplicate filename: {filename}')
        else:
            duplicate_filenames.add(filename)

    # Create dictionaries to store unique and duplicate hashes
    unique_hashes = {}
    duplicate_hashes = {}

    # Loop through files without hash
    for filepath in files_without_hash:
        print("Hashing " + filepath)
        hash_value = get_file_hash(filepath)
        print(hash_value + " is hash for " + filepath)
        if hash_value not in unique_hashes.values():
            unique_hashes[filepath] = hash_value
        else:
            print(filepath + " is a dupe " + hash_value)
            duplicate_hashes[filepath] = hash_value

    # Write unique and duplicate hashes to CSV files
    write_to_csv(unique_hashes, duplicate_hashes)

# Call main function
if __name__ == '__main__':
    dir1 = "/srv/External_6TB_1/root/Videos/"
    dir2 = "/srv/mergerfs/data/Video2/"
    main(dir1,dir2)
