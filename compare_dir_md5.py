import os
import hashlib

def get_sha256(file_path):
    """Return the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    return sha256.hexdigest()

def compare_directories(dir1, dir2):
    """Compare the SHA256 hashes of files in two directories."""
    dir1_files = set()
    dir2_files = set()
    for root, dirs, files in os.walk(dir1):
        for name in files:
            dir1_files.add(os.path.join(root, name))
    for root, dirs, files in os.walk(dir2):
        for name in files:
            dir2_files.add(os.path.join(root, name))
    dir1_hashes = {}
    dir2_hashes = {}
    for file_path in dir1_files:
        dir1_hashes[file_path] = get_sha256(file_path)
    for file_path in dir2_files:
        dir2_hashes[file_path] = get_sha256(file_path)
    for file_path, hash1 in dir1_hashes.items():
        if file_path in dir2_hashes:
            hash2 = dir2_hashes[file_path]
            if hash1 != hash2:
                print(f"File {file_path} differs.")
        else:
            print(f"File {file_path} not found in {dir2}.")
    for file_path in dir2_hashes:
        if file_path not in dir1_hashes:
            print(f"File {file_path} not found in {dir1}.")

# Example usage:
compare_directories("/path/to/dir1", "/path/to/dir2")
