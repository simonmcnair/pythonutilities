import os
import hashlib
import json
import csv

# Step 1: Start
dir1 = 'dir1'  # Directory 1
dir2 = 'dir2'  # Directory 2
cache_file = 'cache.json'  # Cache JSON file
unique_file = 'unique.csv'  # Unique hashes CSV file
duplicate_file = 'duplicate.csv'  # Duplicate hashes CSV file

# Step 2: Read the cache JSON file (if exists) into a dictionary
cache = {}
if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        cache = json.load(f)

# Step 3: Get the file paths from dir1 and dir2 recursively
file_paths = []
for dir_path in [dir1, dir2]:
    for dirpath, _, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_paths.append(file_path)

# Step 4: Sort the file paths by filename
file_paths.sort()

unique_hashes = set()  # Set to store unique hashes
duplicate_hashes = set()  # Set to store duplicate hashes

# Step 5: For each file path
for file_path in file_paths:
    # Extract filename
    filename = os.path.basename(file_path)

    # If filename exists in cache dictionary
    if filename in cache:
        hash_value = cache[filename]
        # Check if hash value is a duplicate
        if hash_value in unique_hashes or hash_value in duplicate_hashes:
            duplicate_hashes.add(hash_value)
            print(f"Duplicate hash: {hash_value} - File path: {file_path}")
        else:
            unique_hashes.add(hash_value)
    else:
        # Print "Processing file: {file_path}"
        print(f"Processing file: {file_path}")

        # Generate SHA256 hash value for file
        hash_object = hashlib.sha256()
        with open(file_path, 'rb') as f:
            while True:
                data = f.read(65536)
                if not data:
                    break
                hash_object.update(data)
        hash_value = hash_object.hexdigest()

        # Update cache dictionary with filename and hash value
        cache[filename] = hash_value

        # Add hash value to unique hashes set
        unique_hashes.add(hash_value)

# Step 6: Write unique hashes set to unique.csv
with open(unique_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Hash', 'Filepath'])
    for hash_value in unique_hashes:
        for filename, value in cache.items():
            if value == hash_value:
                writer.writerow([hash_value, filename])

# Step 7: Write duplicate hashes set to duplicate.csv
with open(duplicate_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Hash', 'Filepath'])
    for hash_value in duplicate_hashes:
        for filename, value in cache.items():
            if value == hash_value:
                writer.writerow([hash_value, filename])

# Step 8: Write cache dictionary to cache.json
with open(cache_file, 'w') as f:
    json.dump(cache, f, indent=4)

# Step 9: End
