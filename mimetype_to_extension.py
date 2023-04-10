import os
import subprocess

def get_file_type(file_path):

    mime_type_to_extension = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'audio/mpeg': '.mp3',
        'audio/wav': '.wav',
        'video/mp4': '.mp4',
        'audio/x-wav': '.wav',
        'audio/wave': '.wav',
        'audio/x-pn-wav': '.wav',
        'audio/flac': '.flac',
        'audio/ogg': '.ogg',
        'audio/x-ms-wma': '.wma',
        'audio/aac': '.aac',
        'audio/x-aiff': '.aif',
        'audio/x-m4a': '.m4a',
        'audio/x-mpegurl': '.m3u',
        'audio/webm': '.webm',
        'audio/x-pn-realaudio': '.ra',
        'audio/x-ms-wax': '.wax',
        'audio/x-pn-au': '.au',
        'audio/x-pn-realaudio-plugin': '.rpm',
        'audio/x-pn-wav': '.wav',
        'audio/midi': '.mid',
        'audio/midi': '.midi',
        'audio/x-midi': '.midi',
        'audio/x-midi': '.mid',
        'audio/basic': '.snd',
        'audio/it': '.it',
        'audio/x-mod': '.mod',
        'audio/xm': '.xm',
        'audio/s3m': '.s3m',
        'audio/xm': '.xm',
        'audio/it': '.it',
        'audio/s3m': '.s3m',
        'audio/xm': '.xm',
        'audio/xm': '.xm',
        'audio/it': '.it',
        'audio/midi': '.midi',
        'audio/midi': '.mid',
        'audio/x-midi': '.mid',
        'audio/x-midi': '.midi',
        'audio/s3m': '.s3m',
        'audio/xm': '.xm',
        'audio/xm': '.xm',
        'audio/x-mod': '.mod',
        'audio/it': '.it',
        'audio/x-midi': '.midi',
        'audio/x-midi': '.mid',
        'audio/x-mod': '.mod',
        'audio/midi': '.mid',
        'audio/midi': '.midi',
        'audio/x-midi': '.midi',
        'audio/x-midi': '.mid',
        'audio/it': '.it',
        'audio/x-mod': '.mod',
        'audio/s3m': '.s3m',
        'audio/xm': '.xm',
        'audio/xm': '.xm',
        'audio/s3m': '.s3m',
        'audio/xm': '.xm',
        'audio/xm': '.xm',
        'audio/x-mod': '.mod',
        'audio/x-pn-wav': '.wav',
        'audio/vnd.dts': '.dts',
        'audio/vnd.dts.hd': '.dtshd',
        # Add more mappings as needed
    }

    try:
        # Run 'file' command and capture the output
        output = subprocess.check_output(['file', '-b', '--mime-type', file_path], stderr=subprocess.PIPE, universal_newlines=True)
        # Extract the mime-type from the output
        mime_type = output.strip()
        print("mime_type: " + mime_type)
        # Extract the file type extension from the MIME type
        file_extension = mime_type_to_extension.get(mime_type)

        #file_extension = mime_type.rsplit('/')
        return file_extension
    except subprocess.CalledProcessError:
        # 'file' command returned a non-zero exit status, file type could not be determined
        return None



def process_directory(dir1):
    """
    Processes all folders in the given directory and renames files with incorrect file extensions.
    
    Args:
        directory (str): The path to the directory.
    """
    for root, dirs, files in os.walk(dir1):
        for file in files:
            file_path = os.path.join(root, file)
            file_extension = get_file_type(file_path)
            if file_extension:
                # Check if the current file extension matches the detected file extension
                if not file.endswith(file_extension):
                    # If not, rename the file with the correct file extension
                    new_file_path = os.path.splitext(file_path)[0] + file_extension
                    os.rename(file_path, new_file_path)
                    print(f"Renamed file: {file_path} -> {new_file_path}")
                else:
                    print("file extension is already correct for: " + file_path)
            else:
                print(f"Could not determine file extension for: {file_path}")


process_directory("dir_to_process")
