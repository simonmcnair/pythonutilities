import os
import hashlib
import json
import csv


def get_file_hashes(dir_path, chunk_size_mb=1024):
    """Generate file hashes for all files in a directory recursively."""
    file_hashes = {}
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            file_path = os.path.join(root, file)
            print("Processing file: ", file_path)  # Print filename before hashing
            file_hash = calculate_file_hash(file_path, chunk_size_mb)
            if file_hash in file_hashes:
                file_hashes[file_hash].append(file_path)
            else:
                file_hashes[file_hash] = [file_path]
    return file_hashes


def calculate_file_hash(file_path, chunk_size_mb=1024):
    """Calculate SHA256 hash of a file."""
    hash_object = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(chunk_size_mb * 1024 * 1024)
            if not chunk:
                break
            hash_object.update(chunk)
    return hash_object.hexdigest()


def update_cache(cache_file_path, file_hashes):
    """Update the JSON cache file with new file hashes."""
    with open(cache_file_path, 'a') as f:
        for file_hash, file_paths in file_hashes.items():
            json.dump({file_hash: file_paths}, f)
            f.write('\n')


def read_cache(cache_file_path):
    """Read the JSON cache file and return the cached file hashes."""
    file_hashes = {}
    if os.path.exists(cache_file_path):
        with open(cache_file_path, 'r') as f:
            for line in f:
                file_hash, file_paths = json.loads(line).popitem()
                file_hashes[file_hash] = file_paths
    return file_hashes


def write_csv(file_path, data, headers):
    """Write data to a CSV file."""
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for row in data:
            writer.writerow(row)


def main(dir1, dir2, cache_file_path, unique_csv_file, duplicate_csv_file, chunk_size_mb=1024):
    """Main function to scan directories, generate file hashes, update cache, and write CSV files."""
    # Read cache file
    file_hashes = read_cache(cache_file_path)

    # Generate file hashes for dir1 and dir2
    dir1_file_hashes = get_file_hashes(dir1, chunk_size_mb)
    dir2_file_hashes = get_file_hashes(dir2, chunk_size_mb)

    # Update cache with new file hashes
    file_hashes.update(dir1_file_hashes)
    file_hashes.update(dir2_file_hashes)
    update_cache(cache_file_path, file_hashes)

    # Get unique file hashes and duplicate file hashes
    unique_hashes = [(file_hash, file_paths[0]) for file_hash, file_paths in file_hashes.items() if len(file_paths) == 1]
    duplicate_hashes = [(file_hash, file_paths) for file_hash, file_paths in file_hashes.items() if len(file_paths) > 1]

    # Write unique and duplicate file hashes to CSV files
    write_csv(unique_csv_file, unique_hashes, ['File Hash', 'File Path'])
    write_csv(duplicate_csv_file, duplicate_hashes, ['File Hash', 'File Paths'])


if __name__ == '__main__':
    # Directory paths and file paths
    dir1 = 'path/to/dir1'
    dir2 = 'path/to/dir2'
    cache_file_path = 'cache.json'
    unique_csv_file
