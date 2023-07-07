import os
import json
import hashlib

# Define the two directories to search
dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2"

# Define the JSON file to store the hashes in
json_file = "hashes.json"

# Create an empty array to store the directory and filename for each file
file_list = []

# Recursively search through dir1 and append directory and filename to file_list
for root, dirs, files in os.walk(dir1):
    for file in files:
        file_path = os.path.join(root, file)
        print("adding " + file_path)
        file_list.append((dir1, file_path))

# Recursively search through dir2 and append directory and filename to file_list
for root, dirs, files in os.walk(dir2):
    for file in files:
        file_path = os.path.join(root, file)
        print("adding " + file_path)
        file_list.append((dir2, file_path))

# Sort the file list by filename
file_list.sort(key=lambda x: x[1])

# Load existing hashes from JSON file
if os.path.isfile(json_file):
    with open(json_file) as f:
        hashes = json.load(f)
else:
    hashes = {}

# Loop through each file in file_list and generate hash if not already present
for directory, filename in file_list:
    if filename not in hashes:
        print("Creating a hash for " + filename)
        with open(os.path.join(directory, filename), "rb") as f:
            file_bytes = f.read()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            hashes[filename] = file_hash
            print(file_hash + "is hash for", filename)
    else:
        print("Hash already exists for", filename)

# Write updated hashes to JSON file
with open(json_file, "w") as f:
    json.dump(hashes, f)

# Create file containing all unique hashes
unique_hashes = set(hashes.values())
with open("unique_hashes.txt", "w") as f:
    for hash in unique_hashes:
        f.write(hash + "\n")
