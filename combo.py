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
from collections import Counter

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

logger = setup_logger(logfilepath)
#logger = setup_logger(logfilepath, logging.debug)
#logger.debug('This is a debug message')
#logger.info('This is an info message')
#logger.warning('This is a warning message')
#logger.error('This is an error message')


# noinspection PyUnresolvedReferences
def image_make_square(img, target_size):
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
def image_smart_resize(img, size):
    # Assumes the image has already gone through image_make_square
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

        image = image_make_square(image, height)
        image = image_smart_resize(image, height)
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


def image_to_wd14_tags(filename, image:Image.Image) \
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
        logger.error("Exception getting tags from image " + filename + ". " + str(e))

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
        logger.error("Exception check_and_del_text_file: " + "Error for " + file_path + ". Retcode: " + str(e.returncode) + " check and del text file:" + str(e.output) + ".")
        return False
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
def delete_file(file_path):
    if '.txt' in file_path.lower():
        try:
            os.remove(file_path)
            logger.info("Deleted file: " + file_path)
            return True
        except OSError as e:
            logger.error("Exception deleting file: " + file_path + ". " + str(e))
            return False
        except subprocess.CalledProcessError as e:
            logger.error("Exception: " + str(e.returncode) + ".  " + str(e.output) + ".  From " + file_path)
            return False
        
    else:
        logger.info(file_path + ".  Can only delete text files")
        return True

def exiftool_get_existing_tags(img_path):
    try:
        existing_tags = subprocess.check_output(['exiftool', '-P', '-s', '-sep', ',', '-XMP:Subject', '-IPTC:Keywords', '-XMP:CatalogSets', '-XMP:TagsList', img_path]).decode().strip()
        #logger.info("exiftool_get_existing_tags.  :" + tag)

        tags_dict = {
            'XMP': [],
            'IPTC': [],
            'CatalogSets': [],
            'TagsList': []
        }

        separator = '\n'

        if '\r\n' in existing_tags:
            print("exiftool_get_existing_tags: rn detected. Windows?")
            separator = '\r\n'

        for tag in existing_tags.split(separator):

            if tag.startswith('Subject'):
                tags_dict['XMP'].extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('Keywords'):
                tags_dict['IPTC'].extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('CatalogSets'):
                tags_dict['CatalogSets'].extend(tag.split(':')[1].strip().split(','))
            elif tag.startswith('TagsList'):
                tags_dict['TagsList'].extend(tag.split(':')[1].strip().split(','))

        logger.debug(img_path + ".  Exiftool output XMP        :" + str(tags_dict['XMP']))
        logger.debug(img_path + ".  Exiftool output IPTC       :" + str(tags_dict['IPTC']))
        logger.debug(img_path + ".  Exiftool output CatalogSets:" + str(tags_dict['CatalogSets']))
        logger.debug(img_path + ".  Exiftool output TagsList   :" + str(tags_dict['TagsList']))

        return tags_dict

    except Exception as e:
        logger.error("Exception in exiftool_get_existing_tags: " + img_path + ". Error: " + str(e))
        return {}
    
def exiftool_del_dupetags(path):
    logger.info("exiftool_del_dupetags: " + path + ": Removing duplicate tags")
    try:
        output_xmp = subprocess.check_output(['exiftool', '-overwrite_original' ,'-P', '-m', '-sep', '##', '-XMP:Subject<${XMP:Subject;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        logger.info("exiftool_del_dupetags success XMP: " + path + ". output: " + output_xmp)
    except Exception as e:
        logger.error("Exception in exiftool_del_dupetags XMP: " + path + ". Error: " + output_xmp + ".  " + str(e))

    try:
        output_iptc = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-m', '-sep', '##', '-iptc:keywords<${iptc:keywords;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        logger.info("exiftool_del_dupetags success IPTC: " + path + ". output: " + output_iptc)
    except Exception as e:
        logger.error("Exception in exiftool_del_dupetags IPTC: " + path + ". Error: " + output_iptc + ".  " + str(e))

    try:
        output_CatalogSets = subprocess.check_output(['exiftool', '-overwrite_original' ,'-P', '-m', '-sep', '##', '-XMP:CatalogSets<${XMP:CatalogSets;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        logger.info("exiftool_del_dupetags success CatalogSets: " + path + ". output: " + output_CatalogSets)
    except Exception as e:
        logger.error("Exception in exiftool_del_dupetags CatalogSets: " + path + ". Error: " + output_CatalogSets + ".  " + str(e))

    try:
        output_TagsList = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-m', '-sep', '##', '-XMP:TagsList<${iptc:TagsList;NoDups}', path], stderr=subprocess.STDOUT, universal_newlines=True)
        logger.info("exiftool_del_dupetags success Tagslist: " + path + ". output: " + output_TagsList)
    except Exception as e:
        logger.error("Exception in exiftool_del_dupetags TagsList: " + path + ". Error: " + output_TagsList + ".  " + str(e))

    return True
    
def exiftool_is_photo_tagged(photo_path):
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
        logger.error("Exception exiftool_is_photo_tagged: "+ "Error " + str(e.returncode) + ".  " + str(e.output) + ".")
        return False
def exiftool_make_photo_tagged(is_tagged, photo_path):
    try:
        if not exiftool_is_photo_tagged(photo_path) :
            output = subprocess.check_output(['exiftool', '-overwrite_original', '-P', '-s', '-XMP-acdsee:tagged=' + is_tagged, photo_path]).decode().strip()
            logger.info(photo_path + ".  Wasn't tagged.  trying to tag as " + is_tagged + " !  Output: " + output)
            if 'updated' in output.lower():
                logger.info(photo_path + ".  successfully tagged as " + is_tagged + " !  Output: " + output)
                return True
            return False
        else:
            logger.info(photo_path + " is already tagged.  Not modifying")
            return True
    except subprocess.CalledProcessError as e:
        logger.error("Exception " + str(e.returncode) + ".  " + str(e.output) + ".  From " + photo_path)
        return False
def exiftool_Update_tags(img_path, tags):
    try:
        cmd = ['exiftool', '-overwrite_original', '-P']
        existing_tags = exiftool_get_existing_tags(img_path)

        updated = False
        for tag_type, existing_tags_list in existing_tags.items():
            for tag in tags:
                tag = tag.strip()
                if tag and tag not in existing_tags_list:
                    logger.info("exiftool_Update_tags: need to add " + tag_type + " field " + tag + " to " + img_path)
                    cmd.append(f'-{tag_type}:{tag_type}+={tag}')
                    updated = True

        if updated:
            cmd.append(img_path)
            try:
                ret = subprocess.run(cmd, stderr=subprocess.STDOUT, universal_newlines=True)
                logger.info("exiftool_Update_tags " + img_path + ".  Exiftool update completed successfully.  " + str(ret))
                return True
            except Exception as e:
                logger.error("Exception in exiftool_Update_tags: error " + str(e))
                return False
        else:
            logger.error("nothing to do, tags are correct")
            return True

    except Exception as e:
        logger.error("Exception in exiftool_Update_tags: error " + str(e))
        return False

def validate_tags(img_path, tags):
    try:
        existing_tags = exiftool_get_existing_tags(img_path)

        missing = False
        for tag_type, existing_tags_list in existing_tags.items():
            for tag in tags:
                tag = tag.strip()

                if tag and tag not in existing_tags_list:
                    logger.info("validate_tags: " + img_path + "." + tag_type + " tag " + str(tag) + " is missing from " + img_path)
                    missing = True
        if missing:
            return True
        else:
            return False

    except subprocess.CalledProcessError as e:
        logger.error("Exception in validate_tags: " + img_path + ". Error " + str(e.returncode) + " removing duplicate tags: " + str(e.output) + ".")
        return False
def find_duplicate_tags_in_file(img_path):
    try:
        existing_tags = exiftool_get_existing_tags(img_path)
        duplicate_tags = {}

        for tag_type, existing_tags_list in existing_tags.items():
            for tag in existing_tags_list:
                if tag and existing_tags_list.count(tag) > 1:
                    if tag not in duplicate_tags:
                        duplicate_tags[tag] = {
                            'count': existing_tags_list.count(tag),
                            'tag_type': [tag_type]
                        }
                    else:
                        duplicate_tags[tag]['count'] += existing_tags_list.count(tag)
                        duplicate_tags[tag]['tag_type'].append(tag_type)

        if duplicate_tags:
            logger.info("Duplicate tags found in " + img_path)
            for tag, info in duplicate_tags.items():
                logger.debug("Duplicate Tags in %s: %s, Count: %s, Tag Types: %s", img_path, tag, info['count'], ', '.join(set(info['tag_type'])))
            return True

        else:
            logger.info("Duplicate Tags not found in " + img_path)
            return False

    except Exception as e:
        print("find_duplicate_tags_in_file Error:" + str(e))


def process_file(image_path):
    #image_path = 'C:\\Users\\Simon\\Downloads\\w6bgPUV.png'
    reprocess = False
    logger.info("Processfile " + " Processing " + image_path)
    output_file = os.path.splitext(image_path)[0] + ".txt"

    if exiftool_is_photo_tagged(image_path) and not reprocess:
        logger.info(image_path + " is already tagged")
        if find_duplicate_tags_in_file(image_path) :
            exiftool_del_dupetags(image_path)
        if  os.path.isfile(output_file):
            logger.info(image_path + ".  Need to process as there is a " + output_file + " file which could be deleted.")
        else:
            logger.info(image_path + ".  All tags are correct and no dupe tags.  Skipping")
            return True
    else:
        logger.info("Processfile " + image_path + " not marked as processed.  Continue processing ")

    try:
        image = Image.open(image_path)
        logger.info("image: " + image_path + " successfully opened.  Continue processing ")
    except Exception as e:
        logger.error("Processfile Exception1: " + " failed to open image : " + image_path + ". Error: " + str(e) + ".  Skipping")
        return False

    try:
        gr_ratings, gr_output_text, gr_tags = image_to_wd14_tags(image_path, image)
        #gr_output_text = gr_output_text + ',tagged'
        tagdict = gr_output_text.split(",")
        logger.info("Processfile tag extract success. " + image_path + ".  caption: " + gr_output_text)
    except Exception as e:
        logger.error("Processfile tag extraction for " + image_path + " didn't work.  Skipping")
        return False

    try:
        tagdict = [substr for substr in tagdict if substr]
    except Exception as e:
        logger.error("Processfile tagdict substr Error " + ".  Well that didn't work.")
   
    try:
        cmd =  exiftool_Update_tags(image_path, tagdict)
        logger.info("exiftool_Update_tags success. " + image_path + ".  output: " + cmd)
    except Exception as e:
        logger.error("Processfile exiftool_Update_tags Exception" + ": Error validating tags. " + ". " + image_path + ". " + str(e) )
        return False
    
    try:
        ret = validate_tags(image_path, tagdict)
        logger.info(image_path + " tags added correctly " + str(ret))
    except Exception as e:
        logger.error("Processfile validate_tags Exception " + ": Error validating tags. " + ". " + image_path + ". " + str(e) )
        return False
        
    try:
        ret = check_and_del_text_file(output_file,gr_output_text)
        logger.info(image_path + " check_and_del success " + str(ret))
    except Exception as e:
        logger.error("Processfile check_and_del_text_file Exception" + ": Error check_and_del_text_file. " + ". " + image_path + ". " + str(e) )
        return False

    try:        
        ret = exiftool_make_photo_tagged('True',image_path)
        logger.info(image_path + " exiftool_make_photo_tagged " + " True " + " success " + str(ret))
        return True
    except Exception as e:
        logger.error("Processfile exiftool_make_photo_tagged Exception" + ": Error making file tagged. " + ". " + image_path + ". " + str(e) )
        return False



def process_images_in_directory(directory):
    # Process each image in the directory
    image_paths = []
    overall_processed_images = 0
    logger.info("Starting")

    logger.info("fetching file list.  This could take a while.")
    for root, dirs, files in sorted(os.walk(directory)):
        #files.sort()

        for file in files:
            # Check if the file is an image
            if file.lower().endswith(IMAGE_EXTENSIONS):
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