import os
import re
from typing import Mapping, Tuple, Dict
import pandas as pd
import cv2
import numpy as np
from PIL import Image
from huggingface_hub import hf_hub_download
from onnxruntime import InferenceSession
import concurrent.futures
import io
import subprocess
# Needs exiftool too


IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.bmp')
TEXT_EXTENSIONS = ('.txt',)



# noinspection PyUnresolvedReferences
def make_square(img, target_size):
    old_size = img.shape[:2]
    desired_size = max(old_size)
    desired_size = max(desired_size, target_size)

    delta_w = desired_size - old_size[1]
    delta_h = desired_size - old_size[0]
    top, bottom = delta_h // 2, delta_h - (delta_h // 2)
    left, right = delta_w // 2, delta_w - (delta_w // 2)

    color = [255, 255, 255]
    return cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)


# noinspection PyUnresolvedReferences
def smart_resize(img, size):
    # Assumes the image has already gone through make_square
    if img.shape[0] > size:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_AREA)
    elif img.shape[0] < size:
        img = cv2.resize(img, (size, size), interpolation=cv2.INTER_CUBIC)
    else:  # just do nothing
        pass

    return img


class WaifuDiffusionInterrogator:
    def __init__(
            self,
            repo='SmilingWolf/wd-v1-4-vit-tagger-v2',
            model_path='model.onnx',
            tags_path='selected_tags.csv',
            mode: str = "auto"
    ) -> None:
        self.__repo = repo
        self.__model_path = model_path
        self.__tags_path = tags_path
        self._provider_mode = mode

        self.__initialized = False
        self._model, self._tags = None, None

    def _init(self) -> None:
        if self.__initialized:
            return

        model_path = hf_hub_download(self.__repo, filename=self.__model_path)
        tags_path = hf_hub_download(self.__repo, filename=self.__tags_path)

        self._model = InferenceSession(str(model_path))
        self._tags = pd.read_csv(tags_path)

        self.__initialized = True

    def _calculation(self, image: Image.Image)  -> pd.DataFrame:
        self._init()

        _, height, _, _ = self._model.get_inputs()[0].shape

        # alpha to white
        image = image.convert('RGBA')
        new_image = Image.new('RGBA', image.size, 'WHITE')
        new_image.paste(image, mask=image)
        image = new_image.convert('RGB')
        image = np.asarray(image)

        # PIL RGB to OpenCV BGR
        image = image[:, :, ::-1]

        image = make_square(image, height)
        image = smart_resize(image, height)
        image = image.astype(np.float32)
        image = np.expand_dims(image, 0)

        # evaluate model
        input_name = self._model.get_inputs()[0].name
        label_name = self._model.get_outputs()[0].name
        confidence = self._model.run([label_name], {input_name: image})[0]

        full_tags = self._tags[['name', 'category']].copy()
        full_tags['confidence'] = confidence[0]

        return full_tags

    def interrogate(self, image: Image) -> Tuple[Dict[str, float], Dict[str, float]]:
        full_tags = self._calculation(image)

        # first 4 items are for rating (general, sensitive, questionable, explicit)
        ratings = dict(full_tags[full_tags['category'] == 9][['name', 'confidence']].values)

        # rest are regular tags
        tags = dict(full_tags[full_tags['category'] != 9][['name', 'confidence']].values)

        return ratings, tags


WAIFU_MODELS: Mapping[str, WaifuDiffusionInterrogator] = {
    'wd14-vit-v2': WaifuDiffusionInterrogator(),
    'wd14-convnext': WaifuDiffusionInterrogator(
        repo='SmilingWolf/wd-v1-4-convnext-tagger'
    ),
}
RE_SPECIAL = re.compile(r'([\\()])')

def check_and_append_text_file(file_path, words):
    # Check if the file exists
    if not os.path.isfile(file_path):
        # If the file doesn't exist, create it and write the words
        log_error("Creating file " + file_path)
        with open(file_path, 'w') as file:
            file.write(words)
    else:
        # Read the contents of the text file
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Split the file contents into individual words
        file_words = set(file_contents.strip().split(','))

        # Split the input words into individual words
        input_words = set(words.strip().split(','))

        # Check if all the input words are present in the file words
        if not input_words.issubset(file_words):
            # Append the input words to the file
            log_error("appending " + words + " to " + file_path)
            with open(file_path, 'a') as file:
                file.write(',' + words)
        else:
            log_error("All words already present in " + file_path)




def image_to_wd14_tags(image:Image.Image) \
        -> Tuple[Mapping[str, float], str, Mapping[str, float]]:
    try:
        model = WAIFU_MODELS['wd14-vit-v2']
        ratings, tags = model.interrogate(image)

        filtered_tags = {
            tag: score for tag, score in tags.items()
            if score >= .35
        }

        text_items = []
        tags_pairs = filtered_tags.items()
        tags_pairs = sorted(tags_pairs, key=lambda x: (-x[1], x[0]))
        for tag, score in tags_pairs:
            tag_outformat = tag
            tag_outformat = tag_outformat.replace('_', ' ')
            tag_outformat = re.sub(RE_SPECIAL, r'\\\1', tag_outformat)
            text_items.append(tag_outformat)
        output_text = ', '.join(text_items)

        return ratings, output_text, filtered_tags
    except Exception as e:
        log_error("error " + e)

def build_command(img_path, tags):
    try:
        cmd = ['exiftool', '-overwrite_original']
        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path]).decode().strip()

        existing_xmp_tags = []
        existing_iptc_tags = []
        for tag in existing_tags.split('\r\n'):
            if tag.startswith('Subject'):
                existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))

        updated = False
        for tag in tags:
            tag = tag.strip()
            if tag and tag not in existing_xmp_tags:
                log_error("need to add xmp field " + tag + " to " + img_path)
                cmd.append(f'-XMP:Subject+={tag}')
                updated = True
            if tag and tag not in existing_iptc_tags:
                log_error("need to add iptc field " + tag + " to " + img_path)
                cmd.append(f'-iptc:keywords+={tag}')
                updated = True

        if updated:
            cmd.append(img_path)
            return cmd
        else:
            return None
    except Exception as e:
        log_error("error " + e)


def validate_tags(img_path, tags):
    try:
        
        #print("Running exiftool command")
        #result = subprocess.run(['exiftool', '-P', '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path], capture_output=True, text=True)
        #output = result.stdout.strip()
        #return_code = result.returncode
        
        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path]).decode().strip()

        if "error" in existing_tags.lower():
            print("Error " + existing_tags)

        existing_xmp_tags = []
        existing_iptc_tags = []
        duplicate_tags = {}  # Dictionary to store duplicate tags and their counts

        for tag in existing_tags.split('\r\n'):
            if tag.startswith('Subject'):
                existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))

        for tag in tags:
            tag = tag.strip()
            if tag and tag not in existing_xmp_tags and tag not in existing_iptc_tags:
                log_error("FAiled to udpate " + tag)
                return False
            elif tag:
                xmp_count = existing_xmp_tags.count(tag)
                iptc_count = existing_iptc_tags.count(tag)
                if xmp_count > 1 or iptc_count > 1:
                    log_error("multiple tag occurance of " + tag)
                    duplicate_tags[tag] = xmp_count + iptc_count  # Store tag and its total count

        if duplicate_tags:
            log_error("Duplicate tags:")
            for tag, count in duplicate_tags.items():
                log_error(f"{tag}: {count} times")  # Print tag and its count

            deldupetags(img_path)

        return True
    except subprocess.CalledProcessError as e:
        log_error("Error removing duplicate tags:", e)
        return False    

def deldupetags(path):
    try:
        print("Removing duplicate tags")
        output_xmp = subprocess.check_output(['exiftool', '-P', '-m', '-sep', '##', '-XMP:Subject<${XMP:Subject;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        output_iptc = subprocess.check_output(['exiftool', '-P', '-m', '-sep', '##', '-iptc:keywords<${iptc:keywords;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        print("Duplicate tags removed successfully.")
        print("XMP output was " + output_xmp)
        print("iptc output was " + output_iptc)
        return True
    except subprocess.CalledProcessError as e:
        print("Error " + e.returncode + " removing duplicate tags:" + e.output + ".")
        return False
    

def log_error(msg):
    print(msg)
    with open('error.log', 'a') as f:
        f.write(msg + '\r\n')

def check_and_del_text_file(file_path, words):
    # Check if the file exists
    if not os.path.isfile(file_path):
        # If the file doesn't exist, create it and write the words
        log_error("No text metadata file exists.  Great " + file_path)
    else:
        # Read the contents of the text file
        with open(file_path, 'r') as file:
            file_contents = file.read()

        # Split the file contents into individual words
        file_words = set(file_contents.strip().split(','))

        # Split the input words into individual words
        input_words = set(words.strip().split(','))

        # Check if all the input words are present in the file words
        if not input_words.issubset(file_words):
            # Append the input words to the file
            log_error("these words:  " + words + "  exist in text file but not image file. " + file_path)
            
        else:
            log_error("Words required and present are : " + words)
            log_error("All words already present in " + file_path + " Delete the file")
            delete_file(file_path)

def delete_file(file_path):
    if '.txt' in file_path.lower():
        try:
            os.remove(file_path)
            log_error("Deleted file: " + file_path)
        except OSError as e:
            log_error("Error deleting file: " + file_path)
            log_error(str(e))
    else:
        log_error("can only delete text files")

def process_file(image_path):
    #image_path = 'C:\\Users\\Simon\\Downloads\\w6bgPUV.png'
    try:
        log_error("Processing " + image_path)
        image = Image.open(image_path)
        output_file = os.path.splitext(image_path)[0] + ".txt"

        gr_ratings, gr_output_text, gr_tags = image_to_wd14_tags(image)

        tagdict = gr_output_text.split(",")
        log_error("caption: " + gr_output_text)

        #Here we have the caption, now we need to read the captions on the files, see if they match, and if not, add any relevant tags to the image file
        cmd = build_command(image_path, tagdict)
        if cmd:
            log_error("tags need updating")
            #log_error(str(cmd))
            try:
                ret = subprocess.run(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                if ret.returncode == 0 :
                    print("Exiftool completed successfully: " + str(ret.returncode))
                if validate_tags(image_path, tagdict):
                    log_error("tags added correctly")
                    check_and_del_text_file(output_file,gr_output_text)
                else:
                    log_error(f"Error: Tags were not added correctly for {image_path}")
            except Exception as e:
                log_error("Error on " + image_path + ". " + str(e) + "command line was: " + (str(cmd)))
        else:
            log_error("no update needed")
            check_and_del_text_file(output_file,gr_output_text)
    except Exception as e:
        log_error("error " + e)


def process_images_in_directory(directory):
    # Process each image in the directory
    image_paths = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            # Check if the file is an image
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                # Get the full path to the image
                image_path = os.path.join(root, file)
                image_paths.append(image_path)

    num_images = len(image_paths)
    processed_images = 0
    average_time_per_image = 0

#    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
 
        # Submit the image processing tasks
        for image_path in image_paths:
            future = executor.submit(process_file, image_path)
            futures.append(future)

        # Iterate over completed futures
        for future in concurrent.futures.as_completed(futures):
            processed_images += 1
            elapsed_time = future.result()
            average_time_per_image = (average_time_per_image * (processed_images - 1) + elapsed_time) / processed_images

            # Update progress bar
            progress = processed_images / num_images
            eta = (num_images - processed_images) * average_time_per_image
            print("Test" + progress + "." + eta)
            update_progress(progress, eta)

    print("Processing complete!")


def update_progress(progress, eta):
    # Update progress bar and ETA
    progress_bar_width = 50
    progress_bar = '=' * int(progress_bar_width * progress)
    percent_complete = int(progress * 100)
    print(f"\r[{progress_bar:<{progress_bar_width}}] {percent_complete}% - ETA: {format_eta(eta)}", end='')


def format_eta(seconds):
    # Format ETA as HH:MM:SS
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# Specify the directory containing the images
#image_directory = 'X:\Stable\dif\stable-diffusion-webui-docker\output'
#image_directory = 'X:\\Stable\\dif\\stable-diffusion-webui-docker\\output\\img2img\\2023-05-17\\'
image_directory = '/srv/dev-disk-by-uuid-e83913b3-e590-4dc8-9b63-ce0bdbe56ee9/Stable/dif/stable-diffusion-webui-docker/output'

# Process the images in the directory and generate captions
process_images_in_directory(image_directory)



 
