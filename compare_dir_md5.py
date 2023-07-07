import os
import hashlib
import json

# Define the two directories to search in
dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2/"

# Define the array to store the directory and filename for both directory trees
files = []

# Recursively list all files in dir1 and dir2 and store the directory and filename in the files array
for root, directories, filenames in os.walk(dir1):
    for filename in filenames:
        print(os.path.join(root, filename))
        files.append((os.path.join(root, filename), dir1))
        
for root, directories, filenames in os.walk(dir2):
    for filename in filenames:
        print(os.path.join(root, filename))
        files.append((os.path.join(root, filename), dir2))

# Sort the files array by filename
#files.sort(key=lambda x: x[0])
files.sort(key=lambda x: os.path.basename(x[0]))

with open("files.txt", "w") as f:
    for file, directory in files:
        f.write(f"{file}\n")

# Read the existing hashes from the json file
existing_hashes = {}
if os.path.exists("hashes.json"):
    with open("hashes.json", "r") as f:
        existing_hashes = json.load(f)

# Loop through each file in the files array, generate a hash for each file that doesn't already have one, and update the hashes json file
unique_hashes = set()
for file, directory in files:
    file_hash = ""
    with open(file, "rb") as f:
        print("hashing " + file)
        file_hash = hashlib.sha256(f.read()).hexdigest()
        print(file_hash + " is hash for " + file)
    if file_hash in existing_hashes:
        print(f"Duplicate hash found: {existing_hashes[file_hash]} and {file}") 
        with open("duplicates.txt", "w") as f:
            f.write(f"{existing_hashes[file_hash]} , {file}, {file_hash} \n")
    else:
        existing_hashes[file_hash] = file
        unique_hashes.add(file_hash)
        
    with open("hashes.json", "w") as f:
        json.dump(existing_hashes, f, indent=4)

# Print out all the unique hashes
print(f"Total unique hashes: {len(unique_hashes)}")
with open("unique_hashes.txt", "w") as f:
    for hash in unique_hashes:
        f.write(f"{hash}\n")
