import os
import hashlib
import csv

def get_sha256(file_path):
    """Return the SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    print("Started creating hash for " + file_path)
    with open(file_path, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
    print("Created hash for " + file_path)
    return sha256.hexdigest()

def compare_directories(dir1, dir2, output_file):
    """Compare the SHA256 hashes of files in two directories and write the results to a CSV file."""
    dir1_files = set()
    dir2_files = set()
    for root, dirs, files in os.walk(dir1):
        for name in files:
            dir_to_add = os.path.join(root, name)
            dir1_files.add(dir_to_add)
            print("adding " + dir_to_add)
    for root, dirs, files in os.walk(dir2):
        for name in files:
            dir_to_add = os.path.join(root, name)
            dir2_files.add(dir_to_add)
            print("adding " + dir_to_add)
    dir1_hashes = {}
    dir2_hashes = {}
    for file_path in dir1_files:
        hash = get_sha256(file_path)
        print (hash + " is hash for " + file_path)
        dir1_hashes[file_path] = hash
    for file_path in dir2_files:
        hash = get_sha256(file_path)
        print (hash + " is hash for " + file_path)
        dir2_hashes[file_path] = hash
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["File", "Directory 1 SHA256", "Directory 2 SHA256", "Status"])
        for file_path, hash1 in dir1_hashes.items():
            if file_path in dir2_hashes:
                hash2 = dir2_hashes[file_path]
                if hash1 == hash2:
                    status = "Match"
                else:
                    status = "Different"
            else:
                status = "Missing in Directory 2"
                hash2 = ""
            writer.writerow([file_path, hash1, hash2, status])
        for file_path, hash2 in dir2_hashes.items():
            if file_path not in dir1_hashes:
                writer.writerow([file_path, "", hash2, "Missing in Directory 1"])

# Example usage:
compare_directories("/srv/External_6TB_1/root/Videos", "/srv/mergerfs/data/Video2", "output.csv")
