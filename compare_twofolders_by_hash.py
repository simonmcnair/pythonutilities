import os
import csv
import hashlib
import time

HASH_CHUNK_SIZE_MB = 64  # Chunk size in MB for hashing

def write_unique_hashes_to_csv(filehashes, output_file):
    # Create a dictionary to store unique file hashes
    unique_filehashes = {}

    # Iterate through the dictionary and add unique file hashes to the dictionary
    file_hash_list = list(filehashes.values())

        # Iterate through the input filehashes dictionary
    for filepath, file_hash in filehashes.items():
        # If the filehash appears for the first time, add it to unique_filehashes
        if file_hash_list.count(file_hash) == 1:
            unique_filehashes[filepath] = file_hash

    if len(unique_hashes) > 0:
    # Write unique file hashes and their corresponding file paths to the CSV file
        with open(output_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['File path', 'File hash'])
            for file_hash, file_path in unique_filehashes.items():
                writer.writerow([file_path, file_hash])
        print(f"Successfully created CSV file with unique file hashes: {output_file}")
    else:
        print("No unique file hashes found. CSV file not created.")


# Directories to scan
#dir1 = "/srv/External_6TB_1/root/Videos/"
#dir2 = "/srv/mergerfs/data/Video2/"

dir1 = "/srv/External_6TB_3/root/Videos/"
dir2 = "/srv/mergerfs/data/Videos/"

#dir1 = "W:\\External_6TB_1\\root\\Videos"
#dir2 = "W:\\mergerfs\\data\Video2\\"

# Filepath for cache.csv
cache_file = 'cache.csv'
#cache_file = 'W:\RAID5\dev-disk-by-uuid-342ac512-ae09-47a7-842f-d3158537d395\mnt\cache.csv'
unique_file = 'unique.csv'
duplicate_file = 'duplicate_hashes.csv'

# Dictionary to store filepaths to be processed
toprocess = {}

# Read cache.csv into filehashes dictionary if it exists
filehashes = {}
if os.path.exists(cache_file):
    print("Loading cache")
    with open(cache_file, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            filehashes[row[0]] = row[1]
    print("cache load complete")

# Function to calculate the blake2 hash of a file
def calculate_hash(file_path):

    chunk_size = HASH_CHUNK_SIZE_MB * 1024 * 1024  # Convert to bytes
    
    file_size = os.path.getsize(file_path)
    file_size_MB = file_size / (1024 * 1024)
    start_time = time.time()
    print(f"Creating hash for file: {file_path}")
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
            processed_bytes_MB = processed_bytes / (1024 * 1024)
                # Print read speed for each chunk
            #print(f'Read speed: {read_speed:.2f} bytes/second')
            print(f'Percentage processed: {percentage_processed:.2f}%.  Read speed: {read_speed:.2f} MBps.  Size: {file_size_MB:.2f} MB.  Processed: {processed_bytes_MB} MB')
            
        end_time = time.time() # End time
        processing_time = end_time - start_time # Calculate processing time
        
        # Print final read speed and processing time
        print(f'Read speed: {read_speed:.2f} bytes/second.  Processing time: {processing_time:.2f} seconds')
        print(f'hash: {hasher.hexdigest()}')

    return hasher.hexdigest()

# Function to process files in a directory recursively
def process_directory(directory):
    i = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            i += 1
            filepath = os.path.join(dirpath, filename)
            toprocess[filepath] = True
    print(str(directory) + " has " + str(i) + " files.")

# Process both directories
print("Loading files")
process_directory(dir1)
process_directory(dir2)

# Remove filepaths from filehashes that are not in toprocess
print("We know " + str(len(filehashes)) + " known hashes.")
filehashes = {k: v for k, v in filehashes.items() if k in toprocess}
print("There are hashes left to process. "  + str(len(toprocess)) + " to do.")

#if len(filehashes) == 0:
#    print("filehashes is empty")
#    exit()

# Initialize dictionaries to store unique and duplicate hashes
unique_hashes = {}
duplicate_hashes = {}

filetodo = sorted(toprocess.keys(), key=lambda x: (os.path.basename(x), x), reverse=True)
# Process files in toprocess in filename order, with multiples of the same filename processed first
i = 0
for filepath in filetodo:
    i +=1
    print(str(i) + " of " + str(len(filetodo)))
    if filepath not in filehashes:
        # Calculate hash for new file
        file_hash = calculate_hash(filepath)
        filehashes[filepath] = file_hash

        # Check if hash exists in filehashes
        with open(cache_file, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for k, v in filehashes.items():
                writer.writerow([k, v])

        if file_hash in filehashes.values():
            # Find all filepaths with the same hash
            duplicate_files = [k for k, v in filehashes.items() if v == file_hash]
            # Print hash and filepaths
            print(f"Duplicate hash: {file_hash}")
            print("Filepaths:")
            for file in duplicate_files:
                print(file)
            # Add hash and filepath to duplicate_hashes dictionary
            duplicate_hashes[file_hash] = duplicate_files
            filehashes[filepath] = file_hash
            with open(duplicate_file, 'w') as csvfile:
                writer = csv.writer(csvfile)
                for k, v in duplicate_hashes.items():
                    writer.writerow([k, ', '.join(v)])
        else:
            # Add hash and filepath to filehashes dictionary
            filehashes[filepath] = file_hash
    else:
        print(filepath + " already hashed.  Load hash")
        # Get hash for existing file
        file_hash = filehashes[filepath]


write_unique_hashes_to_csv(filehashes,'comp-unique.csv')

