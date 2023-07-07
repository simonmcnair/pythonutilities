import os
import json
import hashlib
import csv

# Step 1: Start

# Step 2: Read the cache JSON file (if exists) into a dictionary
cache_dict = {}
if os.path.exists("cache.json"):
    with open("cache.json", "r") as json_file:
        for line in json_file:
            entry = json.loads(line)
            cache_dict.update(entry)

# Step 3: Get the file paths from the two directories recursively
dir1 = "/srv/External_6TB_1/root/Videos/"
dir2 = "/srv/mergerfs/data/Video2/"
all_files = []
for dir_path in [dir1, dir2]:
    for dir_name, _, file_names in os.walk(dir_path):
        for file_name in file_names:
            file_path = os.path.join(dir_name, file_name)
            all_files.append(file_path)

# Step 4: For each file path
unique_hashes = set()
duplicate_hashes = set()
for file_path in all_files:
    if file_path in cache_dict:
        # File path exists in cache dictionary
        hash_value = cache_dict[file_path]
        if hash_value in unique_hashes:
            # Hash value is a duplicate
            duplicate_hashes.add(hash_value)
            print(f"Duplicate hash: {hash_value} - File path: {file_path}")
        else:
            # Hash value is unique
            unique_hashes.add(hash_value)
    else:
        # File path does not exist in cache dictionary
        print("Create hash for " + file_path)
        hash_value = hashlib.sha256()
        with open(file_path, "rb") as file:
            for chunk in iter(lambda: file.read(4096), b""):
                hash_value.update(chunk)
        hash_value = hash_value.hexdigest()

        # Update cache dictionary
        cache_dict[file_path] = hash_value
        unique_hashes.add(hash_value)
        print(f"New hash generated: {hash_value} - File path: {file_path}")

        # Append updated cache dictionary to JSON file
        with open("cache.json", "a") as json_file:
            json.dump({file_path: hash_value}, json_file)
            json_file.write("\n")  # Add newline separator for multiple JSON objects

# Step 5: Write unique_hashes set to unique.csv
with open("unique.csv", "w", newline="") as unique_csv_file:
    writer = csv.writer(unique_csv_file)
    writer.writerow(["Hash", "File Path"])
    for hash_value in unique_hashes:
        for file_path in cache_dict.keys():
            if cache_dict[file_path] == hash_value:
                writer.writerow([hash_value, file_path])

# Step 6: Write duplicate_hashes set to duplicate.csv
with open("duplicate.csv", "w", newline="") as duplicate_csv_file:
    writer = csv.writer(duplicate_csv_file)
    writer.writerow(["Hash", "File Path"])
    for hash_value in duplicate_hashes:
        for file_path in cache_dict.keys():
            if cache_dict[file_path] == hash_value:
                writer.writerow([hash_value, file_path])

# Step 7: Repeat step 4 for the next file path

# Step 8: End
