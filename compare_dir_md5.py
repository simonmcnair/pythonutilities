import os
import json
import hashlib

# Define the two directories to search
dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2"

# define the json file to store the hashes
hash_file = "hashes.json"

# create an empty list to store the file paths and names
file_list = []

# recursively traverse both directories and store the file paths and names
for root, dirs, files in os.walk(dir1):
    for file in files:
        print("Adding " + file)
        file_list.append((root, file))

for root, dirs, files in os.walk(dir2):
    for file in files:
        print("Adding " +file)
        file_list.append((root, file))

# sort the file list by filename
file_list.sort(key=lambda x: x[1])

# open the hash file and load the existing hashes (if any)
hashes = {}
if os.path.exists(hash_file):
    with open(hash_file, "r") as f:
        hashes = json.load(f)

# iterate through the file list and generate hashes for files without one
for path, file in file_list:
    full_path = os.path.join(path, file)
    if full_path not in hashes:
        print("Hashing " + full_path)
        with open(full_path, "rb") as f:
            hash_object = hashlib.sha256()
            hash_object.update(f.read())
            hash_value = hash_object.hexdigest()
        hashes[full_path] = hash_value
        print(f"Generated hash for {full_path}: {hash_value}")

    else:
        print(f"Skipping {full_path}, already hashed")
        # check for duplicates and print them
        duplicate_paths = [p for p in hashes.keys() if hashes[p] == hashes[full_path]]
        if duplicate_path is not None:
            print(f"Duplicate hash value {hashes[full_path]} found for {full_path} and {duplicate_path}")
        else:
            print(f"No duplicate hash value found for {full_path}")

# write the updated hash file
with open(hash_file, "w") as f:
    json.dump(hashes, f, indent=4)

# create a file containing all unique hash values
unique_hashes = list(set(hashes.values()))
unique_hashes.sort()
with open("unique_hashes.txt", "w") as f:
    for hash_value in unique_hashes:
        f.write(hash_value + "\n")
