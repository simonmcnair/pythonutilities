import os
import hashlib
import json
import csv

# Function to recursively list all files in a directory
def list_files(path):
    file_list = []
    for root, dirs, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_list.append(file_path)
    return file_list

# Function to generate SHA256 hash for a file
def generate_hash(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path,"rb") as f:
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

# Function to read existing hash values from a JSON file
def read_hashes(json_file):
    hashes = {}
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            hashes = json.load(f)
    return hashes

# Function to write new hash values to a JSON file
def write_hashes(json_file, hashes):
    with open(json_file, 'w') as f:
        json.dump(hashes, f, indent=4)

# Main program
if __name__ == '__main__':
    # Define the directories to search
    dir1 = "/srv/External_6TB_1/root/Videos/"
    dir2 = "/srv/mergerfs/data/Video2/"


    # List all files in both directories
    files1 = list_files(dir1)
    files2 = list_files(dir2)

    # Combine the file lists and sort by filename
    all_files = sorted(files1 + files2, key=lambda x: os.path.basename(x))

    with open('all_files.txt', 'w') as f:
        f.write('\n'.join(all_files))
        f.write('\n')

    # Read existing hashes from JSON file
    hash_file = 'hashes.json'
    hashes = read_hashes(hash_file)

    # Loop through each file and generate hash if necessary
    duplicates = {}
    for file_path in all_files:
        # Skip files that already have a hash
        if file_path in hashes:
            continue

        # Generate hash for new files
        print("Generating hash for " + file_path)
        hash_value = generate_hash(file_path)
        print(hash_value + " is hash for " + file_path)
        hashes[file_path] = hash_value

        # Check for duplicates
        if hash_value in duplicates:
            duplicates[hash_value].append(file_path)
        else:
            duplicates[hash_value] = [file_path]

        # Update the hash JSON file
        write_hashes(hash_file, hashes)

    # Print duplicate file paths
    for hash_value, file_list in duplicates.items():
        if len(file_list) > 1:
            print(f'Duplicate files with hash {hash_value}:')
            for file_path in file_list:
                print(file_path)

    # Create CSV file of unique hashes
    unique_hashes = set(hashes.values())
    with open('unique_hashes.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Hash Value'])
        for hash_value in unique_hashes:
            writer.writerow([hash_value])
