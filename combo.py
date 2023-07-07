import os
import sys
import re
from typing import Mapping, Tuple, Dict
import pandas as pd
import cv2
import numpy as np
from PIL import Image
from huggingface_hub import hf_hub_download
from onnxruntime import InferenceSession
import concurrent.futures
import subprocess
from datetime import datetime
import logging

#from timer import Timer

# Needs exiftool too



IMAGE_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.tif', '.tiff', '.bmp')
TEXT_EXTENSIONS = ('.txt',)

def setup_logger(log_file_path, log_level=logging.INFO):
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

# Example usage:
cwd = os.getcwd()
logfilepath = os.path.join(cwd, "combolog.txt")

logger = setup_logger(logfilepath, logging.DEBUG)
#logger.debug('This is a debug message')
#logger.info('This is an info message')
#logger.warning('This is a warning message')
#logger.error('This is an error message')


def log_error(msg):
    print(msg)
    with open('error.log', 'a') as f:
        f.write(str(datetime.now()) + ": " + msg + '\r\n')

def get_procedure_name(func):
    def wrapper(*args, **kwargs):
        procedure_name = func.__name__
        print("Procedure name:", procedure_name)
        return func(*args, **kwargs)
    return wrapper

def update_progress(progress, eta):
    # Update progress bar and ETA
    progress_bar_width = 50
    progress_bar = '=' * int(progress_bar_width * progress)
    percent_complete = int(progress * 100)
    logger.info(f"\r[{progress_bar:<{progress_bar_width}}] {percent_complete}% - ETA: {format_eta(eta)}", end='')


def format_eta(seconds):
    # Format ETA as HH:MM:SS
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

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
    try:
        if not os.path.isfile(file_path):
            # If the file doesn't exist, create it and write the words
            logger.info("check_and_append_text_file: Creating file " + file_path)
            with open(file_path, 'w') as file:
                file.write(words)
        else:
            # Read the contents of the text file
            with open(file_path, 'r') as file:
                file_contents = file.read()

            if ',' in file_contents:
                # Split the file contents into individual words
                file_words = set(file_contents.strip().split(','))

                # Split the input words into individual words
                input_words = set(words.strip().split(','))

                # Check if all the input words are present in the file words
                if not input_words.issubset(file_words):
                    # Append the input words to the file
                    logger.info("check_and_append_text_file: appending " + str(words) + " to " + file_path)
                    with open(file_path, 'a') as file:
                        file.write(',' + words)
                else:
                    logger.info("check_and_append_text_file: All words already present in " + file_path)
            else:
                logger.info("check_and_append_text_file: " + file_path + " is not a CSV file")
                return True
            return True

    except Exception as e:
        logger.error("check_and_append_text_file: error " + str(e))
        return False




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
        logger.error("error " + str(e))

def build_command(img_path, tags):
    try:
        cmd = ['exiftool', '-overwrite_original', '-P']
#        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path]).decode().strip()
        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', '-XMP:CatalogSets', '-XMP:TagsList', img_path]).decode().strip()

        existing_xmp_tags = []
        existing_iptc_tags = []
        existing_CatalogSets_tags = []
        existing_TagsList_tags = []
        seperator = '\n'

        if '\r\n' in existing_tags:
            print("buildcommand: rn detected.  Windows ?")
            seperator = '\r\n'
            
    
        for tag in existing_tags.split(seperator):
            if tag.startswith('Subject'):
                existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('CatalogSets'):
                existing_CatalogSets_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('TagsList'):
                existing_TagsList_tags.extend(tag.split(':')[1].strip().split(','))
        
        if not existing_xmp_tags:
            existing_xmp_tags = [substr for substr in existing_xmp_tags if substr]
        if not existing_iptc_tags:
            existing_iptc_tags = [substr for substr in existing_iptc_tags if substr]
        if not existing_CatalogSets_tags:
            existing_CatalogSets_tags = [substr for substr in existing_CatalogSets_tags if substr]
        if not existing_TagsList_tags:
            existing_TagsList_tags = [substr for substr in existing_TagsList_tags if substr]


      #  logger.info(img_path + " Current XMP tags are " + str(existing_xmp_tags))
      #  logger.info(img_path + " Current iptc tags are " + str(existing_iptc_tags))
      #  logger.info(img_path + " Current CatalogSets tags are " + str(existing_CatalogSets_tags))
      #  logger.info(img_path + " Current TagsList tags are " + str(existing_TagsList_tags))
        updated = False
        for tag in tags:
            tag = tag.strip()
            if tag and tag not in existing_xmp_tags:
                logger.info("buildcommand: need to add xmp field " + tag + " to " + img_path)
                cmd.append(f'-XMP:Subject+={tag}')
                updated = True
            if tag and tag not in existing_iptc_tags:
                logger.info("buildcommand: need to add iptc field " + tag + " to " + img_path)
                cmd.append(f'-iptc:keywords+={tag}')
                updated = True
            if tag and tag not in existing_CatalogSets_tags:
                # Add the tag to CatalogSets
                logger.info("buildcommand: need to add catalogset field " + tag + " to " + img_path)
                cmd.append(f'-XMP:CatalogSets+={tag}')
                updated = True
            if tag and tag not in existing_TagsList_tags:
                # Add the tag to tagslist
                logger.info("buildcommand: need to add tagslist field " + tag + " to " + img_path)
                cmd.append(f'-XMP:TagsList+={tag}')
                updated = True
        if updated:
            cmd.append(img_path)
            return cmd
        else:
            return None
    except Exception as e:
        logger.error("buildcommand: error " + str(e))


def dupe_tags(img_path):
    try:
        
        #logger.info("Running exiftool command")
        #result = subprocess.run(['exiftool', '-P', '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path], capture_output=True, text=True)
        #output = result.stdout.strip()
        #return_code = result.returncode
        Dupes = False
        


        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', '-XMP:CatalogSets', '-XMP:TagsList', img_path]).decode().strip()

        existing_xmp_tags = []
        existing_iptc_tags = []
        existing_CatalogSets_tags = []
        existing_TagsList_tags = []
        duplicate_tags = {}  # Dictionary to store duplicate tags and their counts

        seperator = '\n'

        if '\r\n' in existing_tags:
            print("buildcommand: rn detected.  Windows ?")
            seperator = '\r\n'


        for tag in existing_tags.split(seperator):
            if tag.startswith('Subject'):
                existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('CatalogSets'):
                existing_CatalogSets_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('TagsList'):
                existing_TagsList_tags.extend(tag.split(':')[1].strip().split(','))

        if not existing_xmp_tags:
            existing_xmp_tags = [substr for substr in existing_xmp_tags if substr]
        if not existing_iptc_tags:
            existing_iptc_tags = [substr for substr in existing_iptc_tags if substr]
        if not existing_CatalogSets_tags:
            existing_CatalogSets_tags = [substr for substr in existing_CatalogSets_tags if substr]
        if not existing_TagsList_tags:
            existing_TagsList_tags = [substr for substr in existing_TagsList_tags if substr]


        if "error" in existing_tags.lower():
            logger.info("dupe_tags: " + img_path + ".  Error " + existing_tags)
            return False
        
        #logger.info(img_path + " Current XMP tags are " + str(existing_xmp_tags))
        #logger.info(img_path + " Current iptc tags are " + str(existing_iptc_tags))
        #logger.info(img_path + " Current CatalogSets tags are " + str(existing_CatalogSets_tags))
        #logger.info(img_path + " Current TagsList tags are " + str(existing_TagsList_tags))

        xmp_count = existing_xmp_tags.count(tag)
        iptc_count = existing_iptc_tags.count(tag)
        CatalogSets_count = existing_CatalogSets_tags.count(tag)
        TagsList_count = existing_TagsList_tags.count(tag)
        if xmp_count > 1 or iptc_count > 1 or CatalogSets_count > 1 or TagsList_count > 1:
            logger.info("dupe_tags: " + img_path + ".  multiple tag occurance of " + tag)
            duplicate_tags[tag] = xmp_count + iptc_count  # Store tag and its total count
            Dupes = True

        if Dupes:
            logger.info("dupe_tags: " + img_path + ".  Duplicate tags.")
            for tag, count in duplicate_tags.items():
                logger.info(f"dupetags: {tag}: {count} times")  # Print tag and its count
            return True
        else:
            logger.info("dupe_tags: " + img_path + ".  No Duplicate tags.")
            return False
    except subprocess.CalledProcessError as e:
        logger.info("dupe_tags: " + img_path + ".  Error " + str(e.returncode) + " removing duplicate tags:" + str(e.output) + ".")
        return False

def validate_tags(img_path, tags):
    try:
        
        #logger.info("Running exiftool command")
        #result = subprocess.run(['exiftool', '-P', '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path], capture_output=True, text=True)
        #output = result.stdout.strip()
        #return_code = result.returncode
        Dupes = False
        
        #existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', img_path]).decode().strip()
        existing_tags = subprocess.check_output(['exiftool', '-P' , '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', '-XMP:CatalogSets', '-XMP:TagsList', img_path]).decode().strip()

        #exiftool -XMP:Subject-=''

        if "error" in existing_tags.lower():
            logger.info("validate_tags: " + img_path + ".  Error " + existing_tags)
            return False

        existing_xmp_tags = []
        existing_iptc_tags = []
        existing_CatalogSets_tags = []
        existing_TagsList_tags = []
        duplicate_tags = {}  # Dictionary to store duplicate tags and their counts

        seperator = '\n'

        if '\r\n' in existing_tags:
            print("buildcommand: rn detected.  Windows ?")
            seperator = '\r\n'

        for tag in existing_tags.split(seperator):
            if tag.startswith('Subject'):
                existing_xmp_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                existing_iptc_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('CatalogSets'):
                existing_CatalogSets_tags.extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('TagsList'):
                existing_TagsList_tags.extend(tag.split(':')[1].strip().split(','))

        if not existing_xmp_tags:
            existing_xmp_tags = [substr for substr in existing_xmp_tags if substr]
        if not existing_iptc_tags:
            existing_iptc_tags = [substr for substr in existing_iptc_tags if substr]
        if not existing_CatalogSets_tags:
            existing_CatalogSets_tags = [substr for substr in existing_CatalogSets_tags if substr]
        if not existing_TagsList_tags:
            existing_TagsList_tags = [substr for substr in existing_TagsList_tags if substr]

        missing = False
        for tag in tags:
            tag = tag.strip()

            if tag and tag not in existing_xmp_tags and tag not in existing_iptc_tags and tag not in existing_CatalogSets_tags and tag not in existing_TagsList_tags:
                if tag not in existing_xmp_tags:
                    logger.info("validate_tags: " + img_path + ".existing_xmp_tags  tag " + str(tag) + " is missing from " + img_path)
                if tag not in existing_iptc_tags:
                    logger.info("validate_tags: " + img_path + ".existing_iptc_tags  tag " + str(tag) + " is missing from " + img_path)
                if tag not in existing_CatalogSets_tags:
                    logger.info("validate_tags: " + img_path + ".existing_CatalogSets_tags  tag " + str(tag) + " is missing from " + img_path)
                if tag not in existing_TagsList_tags:
                    logger.info("validate_tags: " + img_path + ".existing_TagsList_tags tag " + str(tag) + " is missing from " + img_path)
                missing = True

            elif tag:
                xmp_count = existing_xmp_tags.count(tag)
                iptc_count = existing_iptc_tags.count(tag)
                CatalogSets_count = existing_CatalogSets_tags.count(tag)
                TagsList_count = existing_TagsList_tags.count(tag)
                if xmp_count > 1 or iptc_count > 1 or CatalogSets_count > 1 or TagsList_count > 1:
                    logger.info("validate_tags: " + img_path + ".  multiple tag occurance of " + tag)
                    duplicate_tags[tag] = xmp_count + iptc_count + CatalogSets_count + TagsList_count # Store tag and its total count
                    Dupes = True

        if Dupes:
            logger.info("validate_tags: " + img_path + ".  Duplicate tags.  Try to remove them")
            for tag, count in duplicate_tags.items():
                logger.info(f"{tag}: {count} times")  # Print tag and its count
            deldupetags(img_path)

        if missing == True:
            return False
        return True
    except subprocess.CalledProcessError as e:
        logger.info("validate_tags: " + img_path + ".  Error " + str(e.returncode) + " removing duplicate tags:" + str(e.output) + ".")
        return False

def deldupetags(path):
    try:
        logger.info("deldupetags: " + path + ": Removing duplicate tags")
        output_xmp = subprocess.check_output(['exiftool', '-overwrite_original' ,'-P', '-m', '-sep', '##', '-XMP:Subject<${XMP:Subject;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        output_iptc = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-m', '-sep', '##', '-iptc:keywords<${iptc:keywords;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        output_CatalogSets = subprocess.check_output(['exiftool', '-overwrite_original' ,'-P', '-m', '-sep', '##', '-XMP:CatalogSets<${XMP:CatalogSets;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        output_TagsList = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-m', '-sep', '##', '-iptc:TagsList<${iptc:TagsList;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        logger.info("deldupetags: " + "Duplicate tags removed successfully." + path)
        logger.info("deldupetags: " + path + ": XMP output was " + output_xmp)
        logger.info("deldupetags: " + path + ": iptc output was " + output_iptc)
        logger.info("deldupetags: " + path + ": CatalogSets output was " + output_CatalogSets)
        logger.info("deldupetags: " + path + ": TagsList output was " + output_TagsList)
        return True
    except subprocess.CalledProcessError as e:
        logger.info("deldupetags: " + "Error for " + path + ". Retcode: " + str(e.returncode) + " removing duplicate tags:" + str(e.output) + ".")
        return False
    


def check_and_del_text_file(file_path, words):
    # Check if the file exists
    try:
        if not os.path.isfile(file_path):
            # If the file doesn't exist, create it and write the words
            logger.info("check_and_del_text_file: " + "No text metadata file exists.  Great.  Awesome.  Super.  Smashing.")
            return True
        else:
            # Read the contents of the text file
            logger.info("check_and_del_text_file: " + file_path + " exists.  Checking for text")
            with open(file_path, 'r') as file:
                file_contents = file.read()

            if "," in file_contents:
            # Split the file contents into individual words
                file_words = set(file_contents.strip().split(','))
                
                # Split the input words into individual words
                input_words = set(words.strip().split(','))
                logger.info(file_path + "Words detected from ML are " + words)
                logger.info(file_path + "Words detected from TXT are " + file_contents)
                
                # Check if all the input words are present in the file words
                if not input_words.issubset(file_words):
                    # Append the input words to the file
                    logger.info("check_and_del_text_file: " + "these words:  " + str(words) + "  exist in text file but not image file. " + file_path)
                    return False    
                else:
                    logger.info("check_and_del_text_file: " + "Words required and present are : " + words)
                    logger.info("check_and_del_text_file: " + "All words already present in " + file_path + " Delete the file")
                    delete_file(file_path)
                    return True
            else:
                logger.info("check_and_del_text_file: " + file_path + " is not a csv file.  Skipping")
                return True
    except subprocess.CalledProcessError as e:
        logger.info("check_and_del_text_file: " + "Error for " + file_path + ". Retcode: " + str(e.returncode) + " check and del text file:" + str(e.output) + ".")
        return False
 
def is_photo_tagged(photo_path):
    try:
        output = subprocess.check_output(['exiftool', '-P', '-s', '-XMP-acdsee:tagged', photo_path]).decode().strip()
        #logger.info("output: " + output)
        if 'true' in output.lower():
            #logger.info(photo_path + " already tagged")
            return True
        else:
            #logger.info(photo_path + " untagged.")
            return False
    except subprocess.CalledProcessError as e:
        logger.info("is_photo_tagged: "+ "Error " + str(e.returncode) + ".  " + str(e.output) + ".")
        return False

def make_photo_tagged(photo_path):
    try:
        if not is_photo_tagged(photo_path) :
            output = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-s', '-XMP-acdsee:tagged=true', photo_path]).decode().strip()
            logger.info(photo_path + ".  Wasn't tagged.  Now marked as TAGGED !  Output: " + output)
            if 'updated' in output.lower():
                return True
            return False
        else:
            logger.info(photo_path + " is already tagged.  Not modifying")
            return True
    except subprocess.CalledProcessError as e:
        logger.info("Error " + str(e.returncode) + ".  " + str(e.output) + ".  From " + photo_path)
        return False

def make_photo_untagged(photo_path):
    try:
        output = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-s', '-XMP-acdsee:tagged=false', photo_path]).decode().strip()
        logger.info(photo_path + ".  Marked as unTAGGED !  Output: " + output)
        if 'updated' in output.lower():
            return True
        return False
    except subprocess.CalledProcessError as e:
        logger.info("Error " + str(e.returncode) + ".  " + str(e.output) + ".  From " + photo_path)
        return False

def delete_file(file_path):
    if '.txt' in file_path.lower():
        try:
            os.remove(file_path)
            logger.info("Deleted file: " + file_path)
            return True
        except OSError as e:
            logger.info("Error deleting file: " + file_path)
            logger.info(str(e))
            return False
    else:
        logger.info("can only delete text files")
        return True

def process_file(image_path):
    #image_path = 'C:\\Users\\Simon\\Downloads\\w6bgPUV.png'
    reprocess = False
    try:
        logger.info("Processfile " + " Processing " + image_path)
        output_file = os.path.splitext(image_path)[0] + ".txt"

        if is_photo_tagged(image_path) and not reprocess:
            logger.info(image_path + " is already tagged")
            if dupe_tags(image_path) :
                deldupetags(image_path)
            if  os.path.isfile(output_file):
                logger.info(image_path + ".  Need to process as there is a " + output_file + " file which could be deleted.")
            else:
                logger.info(image_path + ".  All tags are correct and no dupe tags.  Skipping")
                return True
        else:
            logger.info("Processfile " + image_path + " not marked as processed.  Continue processing ")

        try:
            image = Image.open(image_path)
        except Exception as e:
            logger.error("Processfile Exception1: " + " failed to open image : " + image_path + ". Error: " + str(e) + ".  Skipping")
            return False

        try:
            gr_ratings, gr_output_text, gr_tags = image_to_wd14_tags(image)
            #gr_output_text = gr_output_text + ',tagged'
            tagdict = gr_output_text.split(",")
            logger.info("Processfile " + image_path + ".  caption: " + gr_output_text)
        except Exception as e:
            logger.error("Processfile tag extraction for " + image_path + " didn't work.  Skipping")
            return False

        
        try:
            tagdict = [substr for substr in tagdict if substr]
        except Exception as e:
            logger.error("Processfile substr" + "Well that didn't work.")


        #Here we have the caption, now we need to read the captions on the files, see if they match, and if not, add any relevant tags to the image file
        cmd = build_command(image_path, tagdict)
        if cmd:
            logger.info("Processfile " + image_path + ".  Tags need updating")
            #logger.info(str(cmd))
            try:
                ret = subprocess.run(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                logger.debug("Processfile " + image_path + ".  Exiftool update completed without error.  " + str(ret))
                #if ret.returncode == 0 :
                #    logger.info("Exiftool completed successfully: " + str(ret.returncode))
            except Exception as e:
                logger.error("Processfile Exception1: " + " Error updating tags for : " + image_path + ". Error: " + str(e) + ". command line was: " + (str(cmd)))
                return False
            try:
                if validate_tags(image_path, tagdict):
                    logger.info(image_path + " tags added correctly")
                    check_and_del_text_file(output_file,gr_output_text)
                    make_photo_tagged(image_path)
                    return True
                else:
                    logger.info(f"Processfile Error: Tags were not added correctly for {image_path}")
                    return False
            except Exception as e:
                logger.error("Processfile Exception2" + ": Error validating tags: " + ". " + image_path + ". " + str(e) )
                return False

        else:
            logger.info("Processfile " + image_path + ".  Tags are already correct.  Nothing to do.  AWESOME !")
            check_and_del_text_file(output_file,gr_output_text)
            make_photo_tagged(image_path)
            return True
    except Exception as e:
        logger.error("Processfile error3.  Exception: " + image_path + " " + str(e))
        return False


def process_images_in_directory(directory):
    # Process each image in the directory
    image_paths = []
    overall_processed_images = 0
    logger.info("Starting")

    logger.info("fetching file list.  This could take a while.")
    for root, dirs, files in os.walk(directory):
        dirs.sort()
        for file in files:
            # Check if the file is an image
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
                # Get the full path to the image
                image_path = os.path.join(root, file)
                image_paths.append(image_path)
                print("Adding " + image_path)
    logger.info("Done.Array created")

    image_paths.sort()  # Sort the filepaths based on base filenames
    #image_paths.sort(key=lambda x: os.path.basename(x))  # Sort the filepaths based on base filenames

    num_images = len(image_paths)
    logger.info("number of images to process is " + str(num_images))
    processed_images = 0
    average_time_per_image = 0

#    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        completed_count = 0

        # Submit the image processing tasks
        for image_path in image_paths:
            future = executor.submit(process_file, image_path)
            futures.append(future)

        while completed_count < num_images:

            running_count = sum(1 for future in futures if future.running())
            completed_count = sum(1 for future in futures if future.done())
            outstanding_count = num_images - completed_count
            progress = completed_count / num_images * 100
            folderprogress = completed_count / num_images

            overall_processed_images = num_images + completed_count
            overall_progress = overall_processed_images / num_images * 100


            print(f"#################### current folder: {completed_count} of {num_images} files.     {progress:.2f} % complete.  Running: {running_count}, Outstanding: {outstanding_count}")
            #logger.info("#################### overall: " + str(overall_processed_images) + " of " + str(num_images) + " files.     " + str(overall_progress) + '% complete')


    logger.info("finished")

    #            processed_images += 1
    #            overall_processed_images += 1
    #            overallfolderprogress = overall_processed_images / num_images

    #            if future.done():
    #                completed_count += 1
    #                result = future.result()
    #                print(f"Image processed: {result} ({completed_count}/{total_count})")
            # Check if any futures are completed or running
    #    eta = (num_images - processed_images) * average_time_per_image
        
        #for future in concurrent.futures.:

# Specify the directory containing the images

# Process the images in the directory and generate captions
#process_images_in_directory(image_directory)

def execute_script(directory=None):
    if directory is None:
        if os.name == 'nt':  # Windows
            #directory = r'X:\\Stable\\dif\\stable-diffusion-webui-docker\\output'
            directory = r'Z:\\Pron\\Pics\\Sets'
        else:  # Linux or macOS
            directory = '/srv/dev-disk-by-uuid-e83913b3-e590-4dc8-9b63-ce0bdbe56ee9/Stable/dif/stable-diffusion-webui-docker/output'


    # Change the current working directory to the specified directory
    #os.chdir(directory)

    # Execute your script here
    # For demonstration purposes, let's print the current working directory
    #logger.info("Current working directory:", os.getcwd())
    process_images_in_directory(directory)
    logger.info("Processing complete!")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Use the directory provided as a command line argument
        execute_script(sys.argv[1])
    else:
        # Use the predefined directory if no command line argument is provided
        execute_script()