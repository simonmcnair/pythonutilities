import os
import csv
import hashlib
import time

HASH_CHUNK_SIZE_MB = 64  # Chunk size in MB for hashing

def get_file_hashes(dir_path):
    """
    Generate file hashes using Blake2b algorithm for all files in a directory and its subdirectories.

    Args:
        dir_path (str): Directory path.

    Returns:
        dict: Dictionary containing file paths as keys and their corresponding hashes as values.
    """
    file_hashes = {}
    chunk_size = HASH_CHUNK_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    for dirpath, _, filenames in os.walk(dir_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            file_size = os.path.getsize(file_path)
            start_time = time.time()
            print(f"Processing file: {file_path}")
            hasher = hashlib.blake2b()
            read_speed = 0.0 # Initialize read speed to 0 bytes/second
            processed_bytes = 0 # Initialize processed bytes to 0
            with open(file_path, 'rb') as file:
                while True:
                    chunk = file.read(chunk_size)
                    if not chunk:
                        break
                    hasher.update(chunk)


                    processed_bytes += len(chunk)
                    elapsed_time = time.time() - start_time # Elapsed time since start
                    if elapsed_time > 0:
                            # Update read speed based on processed bytes and elapsed time
                            read_speed = (processed_bytes / elapsed_time) / (1024 * 1024)
                    percentage_processed = (processed_bytes / file_size) * 100
                
                        # Print read speed for each chunk
                    #print(f'Read speed: {read_speed:.2f} bytes/second')
                    print(f'Percentage processed: {percentage_processed:.2f}.  Read speed: {read_speed:.2f} MBps')
                    
                end_time = time.time() # End time
                processing_time = end_time - start_time # Calculate processing time
                
                # Print final read speed and processing time
                print(f'Read speed: {read_speed:.2f} bytes/second')
                print(f'Processing time: {processing_time:.2f} seconds')




            file_hashes[file_path] = hasher.hexdigest()

    return file_hashes

def update_cache(cache_file, file_hashes):
    """
    Update CSV cache file with new file hashes.

    Args:
        cache_file (str): Path to CSV cache file.
        file_hashes (dict): Dictionary containing file paths and their corresponding hashes.
    """
    cache_data = []
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            reader = csv.reader(f)
            cache_data = list(reader)

    with open(cache_file, 'w', newline='') as f:
        writer = csv.writer(f)
        for file_path, file_hash in file_hashes.items():
            row = [file_path, file_hash]
            if row not in cache_data:
                writer.writerow(row)

def write_csv(file_path, data):
    """
    Write data to a CSV file.

    Args:
        file_path (str): Path to the CSV file.
        data (list): List of lists representing the data to be written to the CSV file.
    """
    with open(file_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(data)

def main(dir1, dir2, cache_file, unique_hashes_file, duplicate_hashes_file):
    """
    Main function to scan two directories recursively, generate file hashes, and update cache and CSV files.

    Args:
        dir1 (str): Path to the first directory.
        dir2 (str): Path to the second directory.
        cache_file (str): Path to the CSV cache file.
        unique_hashes_file (str): Path to the CSV file for storing unique hashes.
        duplicate_hashes_file (str): Path to the CSV file for storing duplicate hashes.
    """
    # Step 1: Get file hashes for dir1
    file_hashes_dir1 = get_file_hashes(dir1)

    # Step 2: Get file hashes for dir2
    file_hashes_dir2 = get_file_hashes(dir2)

    # Step 3: Combine file hashes from both directories
    all_file_hashes = file_hashes_dir1.copy()
    all_file_hashes.update(file_hashes_dir2)

    # Step 4: Detect unique and duplicate hashes
    unique_hashes = []
    duplicate_hashes = []
    hash_set = set()
    for file_path, file_hash in all_file_hashes.items():
        if file_hash not in hash_set:
            hash_set.add(file_hash)
            unique_hashes.append([file_hash, file_path])
            update_cache(cache_file, all_file_hashes)  # Update cache after each hash is created
        else:
            duplicate_hashes.append([file_hash, file_path])

    # Step 5: Update CSV files
    update_cache(cache_file, all_file_hashes)
    write_csv(unique_hashes_file, unique_hashes)
    write_csv(duplicate_hashes_file, duplicate_hashes)

    print("Unique Hashes:")
    for row in unique_hashes:
        print(f"{row[0]}: {row[1]}")
    print("Duplicate Hashes:")
    for row in duplicate_hashes:
        print(f"{row[0]}: {row[1]}")

if __name__ == '__main__':
    dir1 = "/srv/External_6TB_1/root/Videos/"
    dir2 = "/srv/mergerfs/data/Video2/"
    cache_file = 'cache.csv'
    unique_hashes_file = 'unique_hashes.csv'
    duplicate_hashes_file = 'duplicate_hashes.csv'
    main(dir1, dir2, cache_file, unique_hashes_file, duplicate_hashes_file)
