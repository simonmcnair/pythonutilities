import os
import hashlib
import re
import csv
import signal
import sys

#import concurrent.futures
from pydub import AudioSegment

def signal_handler(sig, frame):
    print("Ctrl+C received. Exiting gracefully...")
    # Perform cleanup operations here, if needed
    sys.exit(0)

# Register the signal handler for Ctrl+C
signal.signal(signal.SIGINT, signal_handler)

# Example struct-like class to store audio file information
class AudioFileInfo:
    def __init__(self, title, artist, album, genre, bitrate, sample_rate, channels, duration, frame_count, format):
        self.title = title
        self.artist = artist
        self.album = album
        self.genre = genre
        self.bitrate = bitrate
        self.sample_rate = sample_rate
        self.channels = channels
        self.duration = duration
        self.frame_count = frame_count
        self.format = format

def get_audio_data(filepath):
    # Load audio file using pydub
    audio_file = AudioSegment.from_file(filepath)

    try:
        # Extract information from audio file
        title = audio_file.tags.get("title")
        artist = audio_file.tags.get("artist")
        album = audio_file.tags.get("album")
        genre = audio_file.tags.get("genre")
        bitrate = audio_file.frame_rate
        sample_rate = audio_file.frame_rate
        channels = audio_file.channels
        duration = audio_file.duration_seconds
        frame_count = audio_file.frame_count()
        format = audio_file.format

        # Create AudioFileInfo object to store extracted information
        audio_info = AudioFileInfo(title, artist, album, genre, bitrate, sample_rate, channels, duration, frame_count, format)

        # Access extracted information from AudioFileInfo object
        print("Title:", audio_info.title)
        print("Artist:", audio_info.artist)
        print("Album:", audio_info.album)
        print("Genre:", audio_info.genre)
        print("Bitrate:", audio_info.bitrate)
        print("Sample Rate:", audio_info.sample_rate)
        print("Channels:", audio_info.channels)
        print("Duration:", audio_info.duration, "seconds")
        print("Frame Count:", audio_info.frame_count)
        print("Format:", audio_info.format)
    except:
        return None

def atoi(text):
    return int(text) if text.isdigit() else text

def natural_keys(text):
    '''
    alist.sort(key=natural_keys) sorts in human order
    http://nedbatchelder.com/blog/200712/human_sorting.html
    (See Toothy's implementation in the comments)
    '''
    return [ atoi(c) for c in re.split(r'(\d+)', text) ]

def move_file(src_path, dst_path):
    """
    Move a file from src_path to dst_path. If a file with the same name already
    exists at the destination path, append a counter to the file name.
    """
    if not os.path.isfile(src_path):
        raise ValueError(f"{src_path} is not a file")

    base_name, ext = os.path.splitext(os.path.basename(src_path))
    dst_base_path = os.path.join(os.path.dirname(dst_path), base_name)

    i = 0
    while True:
        if i == 0:
            dst_file_path = f"{dst_base_path}{ext}"
        else:
            dst_file_path = f"{dst_base_path}_{i}{ext}"

        if not os.path.exists(dst_file_path):
            break

        i += 1

    os.rename(src_path, dst_file_path)
    print("file " + src_path + " moved to " + dst_file_path)

def createhash(filetohash):
    print("Hashing " + filetohash)
    try:
        audio = AudioSegment.from_file(filetohash)
        hash = hashlib.blake2b(audio.raw_data, digest_size=16).hexdigest()
        print(hash + " is hash for " + filetohash)
        return hash
    except:
        print("badfile")
        return None


def main():
    # num_threads = int(input("Enter the number of threads to use: "))
    file_hashes = {}
    print("starting")
    audio_extensions = ['.mp3', '.wav', '.ogg', '.flac']
    pydub_supported_formats = ['.mp3', '.wav', '.aiff', '.flac', '.m4a', '.ogg', '.aac', '.ac3', '.wma']

    for root, dirs, files in os.walk(directory):
        #dirs.sort(key=natural_keys)
        for dir in sorted(dirs):
                dir_path = os.path.join(root, dir)
                print("Processing directory: " + root)
                for file in os.listdir(dir_path):
                    #print("Processing " + file)
                    if file.endswith(tuple(pydub_supported_formats)):
                        file_path = os.path.join(dir_path, file)
                        print(file_path + " Supported file type")

                        get_audio_data(file_path)
                        audio = AudioSegment.from_file(file_path)
                        audiohash =  hashlib.blake2b(audio.raw_data, digest_size=16).hexdigest()
                        # Dictionary to store file hashes and their paths
                        with open(f'allHashes.txt', 'a') as f1:
                            f1.write(file_path + ","  "," + audiohash + "\n")
                        print(file_path + " hash is " + audiohash)
                        if audiohash in file_hashes:
                            print(file_path + " IS a duplicate !!!!!")
                            dupe = file_hashes[audiohash]
                            with open(f'allHashes.txt', 'a') as f1, open(f'duplicates.txt', 'a') as f2:
                                f2.write(file_path + "," + dupe + "," + audiohash + "\n")
                            move_file(file_path,'/srv/RAID5/dev-disk-by-uuid-342ac512-ae09-47a7-842f-d3158537d395/mnt/Audio/dupes/')
                        else:
                            print(file_path + " not a duplicate so far")
                            file_hashes[audiohash] = file_path

# Function to process files in a directory recursively
def process_directory(directory):
    i = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            i += 1
            filepath = os.path.join(dirpath, filename)
            print("adding " + filepath)
            toprocess[filepath] = True
    print(str(directory) + " has " + str(i) + " files.")

# Initialize dictionaries to store unique and duplicate hashes
unique_hashes = {}
duplicate_hashes = {}

#directory = input("Enter the directory path to search for audio files: ")
#directory = "/srv/RAID5/dev-disk-by-uuid-342ac512-ae09-47a7-842f-d3158537d395/mnt/Audio/forbeets/Albums/Henrik Schwarz/DJ Kicks"
#directory = "/srv/RAID5/dev-disk-by-uuid-342ac512-ae09-47a7-842f-d3158537d395/mnt/Audio/forbeets/"
directory = "Z:\\Audio\\forbeets\\"

programname = "mp3hasher"
# Filepath for cache.csv
cache_file = programname + 'cache.csv'
#cache_file = 'W:\RAID5\dev-disk-by-uuid-342ac512-ae09-47a7-842f-d3158537d395\mnt\cache.csv'
unique_file = programname + 'unique.csv'
duplicate_file = programname + 'duplicate_hashes.csv'
pydub_supported_formats = ['.mp3', '.wav', '.aiff', '.flac', '.m4a', '.ogg', '.aac', '.ac3', '.wma']

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

# Process both directories
print("Loading files")
process_directory(directory)


# Remove filepaths from filehashes that are not in toprocess
print("Removing " + str(len(filehashes)) + " known hashes.")
filehashes = {k: v for k, v in filehashes.items() if k in toprocess}
print("Known hashes removed. "  + str(len(toprocess)) + " to do.")


filetodo = sorted(toprocess.keys(), key=lambda x: (os.path.basename(x), x), reverse=True)
# Process files in toprocess in filename order, with multiples of the same filename processed first
i = 0
for filepath in filetodo:
    i +=1
    print(str(i) + " of " + str(len(filetodo)))

    if filepath.endswith(tuple(pydub_supported_formats)):


        if filepath not in filehashes:
            # Calculate hash for new file
            file_hash = createhash(filepath)


            result = get_audio_data(filepath)
            if result is not None:
                print("Has metadata")
            else:
                print("no metadata")



            if file_hash is not None:
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
                print("bad file " + filepath)
        else:
            # Get hash for existing file
            file_hash = filehashes[filepath]
            print("existing hash found and loaded for " + filepath)
        # Add hash and filepath to unique_hashes dictionary
        unique_hashes[file_hash] = filepath
        # Write hash and filepath to cache.csv

with open(unique_file, 'w') as csvfile:
    writer = csv.writer(csvfile)
    for k, v in unique_hashes.items():
        writer.writerow([k, v])
