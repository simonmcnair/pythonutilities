import os
import json
import hashlib
import datetime

# define the two directories to compare
dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2"

# create a set of all filenames in both directories
dir1_files = set(os.listdir(dir1))
dir2_files = set(os.listdir(dir2))
all_files = dir1_files.union(dir2_files)

# create an array to store the directory and filename for both directory trees
file_array = []

# add filenames to the file array with their respective directory
for filename in all_files:
    if filename in dir1_files:
        file_array.append((dir1, filename))
    if filename in dir2_files:
        file_array.append((dir2, filename))

# sort the file array by filename
file_array.sort(key=lambda x: x[1])

# read the existing hash json file or create a new one if it doesn't exist
hash_file = "hashes.json"
if os.path.isfile(hash_file):
    with open(hash_file) as f:
        hash_dict = json.load(f)
else:
    hash_dict = {}

# create a log file to store filenames
log_file = "file_log.txt"
with open(log_file, "w") as f:
    f.write(f"Log created on {datetime.datetime.now()}\n\n")

# loop through the file array and generate a hash for each pair of identical filenames
for i in range(len(file_array)-1):
    if file_array[i][1] == file_array[i+1][1]:
        file1 = os.path.join(file_array[i][0], file_array[i][1])
        file2 = os.path.join(file_array[i+1][0], file_array[i+1][1])
        if file1 not in hash_dict and os.path.isfile(file1):
            with open(file1, "rb") as f1:

                print("Generating a hash for " + file1)
                hash1 = hashlib.sha256(f1.read()).hexdigest()
                print(hash1 + " is hash for " +file1)

            hash_dict[file1] = hash1
            with open(hash_file, "w") as f:
                json.dump(hash_dict, f)
        if file2 not in hash_dict and os.path.isfile(file2):
            with open(file2, "rb") as f2:
                print("Generating a hash for " + file2)
                hash2 = hashlib.sha256(f2.read()).hexdigest()
                print(hash1 + " is hash for " +file2)
            hash_dict[file2] = hash2
            with open(hash_file, "w") as f:
                json.dump(hash_dict, f)
        if hash_dict.get(file1) == hash_dict.get(file2):
            print(f"Duplicate: {file1}, {file2}")
            with open(log_file, "a") as f:
                f.write(f"{file1}, {file2}\n")

# create a list of filenames where the hash is not the same
different_hashes = []
for i in range(len(file_array)-1):
    if file_array[i][1] == file_array[i+1][1]:
        file1 = os.path.join(file_array[i][0], file_array[i][1])
        file2 = os.path.join(file_array[i+1][0], file_array[i+1][1])
        if file1 in hash_dict and file2 in hash_dict and hash_dict[file1] != hash_dict[file2]:
            different_hashes.append(file_array[i][1])

# print the list of filenames with different hashes
print(f"Files with different hashes: {different_hashes}")
with open(log_file, "a") as f:
    f.write(f"\nFiles with different hashes: {different_hashes}")
