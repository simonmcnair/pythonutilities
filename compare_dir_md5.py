import os
import json
import hashlib
import csv

# define the directories to compare
dir1 = '/path/to/dir1'
dir2 = '/path/to/dir2'

# define the cache file to store the file paths and hashes
cache_file = 'cache.json'

# define the output csv files
diff_file = 'differences.csv'
identical_file = 'identical.csv'

# check if cache file exists
if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        cache = json.load(f)
else:
    cache = {}

# loop through each directory and generate hashes for each file
for directory in [dir1, dir2]:
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            if file_path in cache:
                # skip hash generation if hash already exists for file path
                continue
            with open(file_path, 'rb') as f:
                file_hash = hashlib.sha256(f.read()).hexdigest()
                cache[file_path] = file_hash
                # update the cache file with the new hash
                with open(cache_file, 'w') as f:
                    json.dump(cache, f)

# compare the hashes for each directory and create csv files
diff_hashes = {}
identical_hashes = {}
for file_path, file_hash in cache.items():
    if file_path.startswith(dir1):
        file_path2 = file_path.replace(dir1, dir2)
        if os.path.exists(file_path2):
            with open(file_path2, 'rb') as f:
                file_hash2 = hashlib.sha256(f.read()).hexdigest()
            if file_hash != file_hash2:
                # add to differences if hashes don't match
                diff_hashes[file_path] = (file_hash, file_path2, file_hash2)
            else:
                # add to identical groups if hashes match
                identical_hashes.setdefault(file_hash, []).append(file_path)
                identical_hashes[file_hash].append(file_path2)
        else:
            # add to differences if file doesn't exist in dir2
            diff_hashes[file_path] = (file_hash, None, None)
    elif file_path.startswith(dir2):
        # already processed in previous if block
        continue

# write differences to csv file
with open(diff_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['File Path 1', 'Hash 1', 'File Path 2', 'Hash 2'])
    for file_path, hashes in diff_hashes.items():
        writer.writerow([file_path, hashes[0], hashes[1], hashes[2]])

# write identical groups to csv file
with open(identical_file, 'w') as f:
    writer = csv.writer(f)
    writer.writerow(['Hash', 'File Paths'])
    for file_hash, file_paths in identical_hashes.items():
        writer.writerow([file_hash, ', '.join(file_paths)])
