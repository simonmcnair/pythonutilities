import os
import hashlib
import json

dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2/"
file_array = []

# Recursively walk through both directories and add filenames to the file_array
for root, dirs, files in os.walk(dir1):
    for file in files:
        print(os.path.join(root, file))
        file_array.append((os.path.join(root, file), 'dir1'))
        
for root, dirs, files in os.walk(dir2):
    for file in files:
        print(os.path.join(root, file))
        file_array.append((os.path.join(root, file), 'dir2'))

# Sort the file_array by filename
file_array.sort(key=lambda x: os.path.basename(x[0]))

with open("files.txt", "w") as f:
    for file, directory in file_array:
        f.write(f"{file}\n")

# Load existing hashes from the JSON file
existing_hashes = {}
if os.path.exists('hashes.json'):
    with open('hashes.json', 'r') as f:
        existing_hashes = json.load(f)

# Loop through each file in the file_array and generate a hash if it doesn't already exist
for file_path, dir_name in file_array:
    if file_path not in existing_hashes:
        with open(file_path, 'rb') as f:
            print("hashing " + file_path)
            file_hash = hashlib.sha256(f.read()).hexdigest()
            print(file_hash + " is hash for " + file_path)
            existing_hashes[file_path] = file_hash
            with open('hashes.json', 'w') as out_file:
                json.dump(existing_hashes, out_file)

    # Print out any files with identical hashes
    identical_files = [k for k, v in existing_hashes.items() if v == existing_hashes[file_path] and k != file_path]
    if identical_files:
        print(f"{os.path(file_path)} , {identical_files}")
    with open('dupes.txt', 'w') as f:
        f.write(f"{os.path(file_path)} , {identical_files}\n")

# Write out a file containing all the unique hashes
unique_hashes = list(set(existing_hashes.values()))
with open('unique_hashes.txt', 'w') as f:
    f.write('\n'.join(unique_hashes))
