import os
import hashlib
import json
import csv

# Function to calculate SHA256 hash
def calculate_hash(filepath):
    with open(filepath, 'rb') as f:
        file_data = f.read()
        sha256_hash = hashlib.sha256()
        sha256_hash.update(file_data)
        return sha256_hash.hexdigest()

# Function to generate CSV file
def generate_csv(filename, data):
    with open(filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Hash', 'Filepath'])
        for row in data:
            writer.writerow(row)

# Function to read cache.json file
def read_cache():
    cache_data = []
    if os.path.exists('cache.json'):
        with open('cache.json', 'r') as f:
            cache_data = json.load(f)
    return cache_data

# Function to write cache.json file
def write_cache(data):
    with open('cache.json', 'w') as f:
        json.dump(data, f)

# Function to process files in directories and create arrays
def process_files(dir1, dir2):
    all_files = []
    unique_hashes = []
    duplicate_hashes = []
    cache_data = read_cache()

    for dir_path in [dir1, dir2]:
        for dir_name, subdir_list, file_list in os.walk(dir_path):
             for file_name in file_list:
               filepath = os.path.join(dir_name, file_name)
               print("Adding " + filepath)
               all_files.append(filepath)

    all_files.sort(key=lambda x: os.path.basename(x))

    for file in all_files:
        if file not in cache_data:
            print("Creating hash for " + file)
            file_hash = calculate_hash(file)
            file_data = {file, file_hash}
           # file_data = {'Filepath': file, 'Hash': file_hash}
            unique_hashes.append([file_hash, file])
            print(f'{file_hash} is hash for : {file}' + str(file_data))
            cache_data.append(file_data)
            write_cache(cache_data)
        else:
            duplicate_hashes.append([file_hash, file])
            print(f'Duplicate filepath: {file}')

    generate_csv('unique_hashes.csv', unique_hashes)
    generate_csv('duplicate_hashes.csv', duplicate_hashes)

# Main program
if __name__ == '__main__':
    dir1 = "/srv/External_6TB_1/root/Videos/"
    dir2 = "/srv/mergerfs/data/Video2/"
    process_files(dir1, dir2)
