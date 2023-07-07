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
        print("Creating file " + file_path)
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
            print("appending " + words + " to " + file_path)
            with open(file_path, 'a') as file:
                file.write(',' + words)
        else:
            print("All words already present in " + file_path)

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
        print("error " + e)

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
                print("need to add xmp field " + tag + " to " + img_path)
                cmd.append(f'-XMP:Subject+={tag}')
                updated = True
            if tag and tag not in existing_iptc_tags:
                print("need to add iptc field " + tag + " to " + img_path)
                cmd.append(f'-iptc:keywords+={tag}')
                updated = True

        if updated:
            cmd.append(img_path)
            return cmd
        else:
            return None
    except Exception as e:
        print("error " + e)

def validate_tags(img_path, tags):
    existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path]).decode().strip()

    existing_xmp_tags = []
    existing_iptc_tags = []
    for tag in existing_tags.split('\r\n'):
        if tag.startswith('Subject'):
            existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
        elif tag.startswith('Keywords'):
            existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))

    for tag in tags:
        tag = tag.strip()
        if tag and tag not in existing_xmp_tags and tag not in existing_iptc_tags:
            return False

    return True

def log_error(msg):
    with open('error.log', 'a') as f:
        f.write(msg)

def check_and_del_text_file(file_path, words):
    # Check if the file exists
    if not os.path.isfile(file_path):
        # If the file doesn't exist, create it and write the words
        print("No text metadata file exists.  Great " + file_path)
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
            print("these words:  " + words + "  exist in text file but not image file. " + file_path)
            
        else:
            print("Words required and present are : " + words)
            print("All words already present in " + file_path + " Delete the file")
            delete_file(file_path)

def delete_file(file_path):
    if '.txt' in file_path.lower():
        try:
            os.remove(file_path)
            print("Deleted file: " + file_path)
        except OSError as e:
            print("Error deleting file: " + file_path)
            print(str(e))
    else:
        print("can only delete text files")

def process_file(image_path):
    #image_path = 'C:\\Users\\Simon\\Downloads\\w6bgPUV.png'
    try:
        print("Processing " + image_path)
        image = Image.open(image_path)
        output_file = os.path.splitext(image_path)[0] + ".txt"

        gr_ratings, gr_output_text, gr_tags = image_to_wd14_tags(image)

        tagdict = gr_output_text.split(",")
        print("caption: " + gr_output_text)

        #Here we have the caption, now we need to read the captions on the files, see if they match, and if not, add any relevant tags to the image file


        cmd = build_command(image_path, tagdict)
        if cmd:
            print("tags need updating")
            print(str(cmd))
            try:
                subprocess.run(cmd)
                if validate_tags(image_path, tagdict):
                    print("tags added correctly")
                    check_and_del_text_file(output_file,gr_output_text)
                else:
                    log_error(f"Error: Tags were not added correctly for {image_path}")
            except Exception as e:
                print("Error on " + image_path + ". " + str(e))
        else:
            print("no update needed")
            check_and_del_text_file(output_file,gr_output_text)
    except Exception as e:
        print("error " + e)


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

    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Process the images concurrently
        executor._max_workers=4
        executor.map(process_file, image_paths)

# Specify the directory containing the images
#image_directory = 'X:\Stable\dif\stable-diffusion-webui-docker\output'
image_directory = '/output'

# Process the images in the directory and generate captions
process_images_in_directory(image_directory)



 
