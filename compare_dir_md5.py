import os
import hashlib
import json
import csv

# define the two directories to compare
dir1 = 'path/to/dir1'
dir2 = 'path/to/dir2'

# define the cache file name
cache_file = 'hashes.json'

# define the output file names
diff_file = 'diff.csv'
identical_file = 'identical.csv'

# helper function to generate the hash of a file
def generate_hash(file_path):
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            sha256.update(chunk)
    return sha256.hexdigest()

# check if the cache file exists and load its contents if it does
if os.path.exists(cache_file):
    with open(cache_file, 'r') as f:
        cache = json.load(f)
else:
    cache = {}

# iterate over the files in both directories and generate hashes
for directory in [dir1, dir2]:
    files = os.listdir(directory)
    files.sort()  # sort the files by name
    for file_name in files:
        file_path = os.path.join(directory, file_name)
        if file_path not in cache:
            hash_value = generate_hash(file_path)
            cache[file_path] = hash_value
            with open(cache_file, 'w') as f:
                json.dump(cache, f)

# compare the hashes of the files in the two directories
differences = []
identical_groups = []
for file_path in cache:
    if dir1 in file_path:
        other_path = file_path.replace(dir1, dir2)
        if other_path in cache:
            if cache[file_path] != cache[other_path]:
                differences.append((file_path, other_path))
            else:
                identical_groups.append((cache[file_path], file_path, other_path))

# write the differences to a CSV file
with open(diff_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['File in ' + dir1, 'Hash in ' + dir1, 'File in ' + dir2, 'Hash in ' + dir2])
    for diff in differences:
        writer.writerow(diff)

# write the identical groups to a CSV file
with open(identical_file, 'w', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['Hash', 'File in ' + dir1, 'File in ' + dir2])
    for group in identical_groups:
        writer.writerow(group)
