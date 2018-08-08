
import subprocess
from ffprobe import FFProbe

from helper import is_number

import Algorithmia

import secret

from PIL import Image, ImageOps

from pathlib import Path

import shutil

import os

import requests

import urllib

class VideoStabilisingException(Exception):
    pass


class VideoBrokenException(Exception):
    pass


class SuperRes(object):

    def __init__(self):
        self.client = Algorithmia.client(secret.algo_id)
        self.algo = self.client.algo('deeplearning/ColorfulImageColorization/1.1.13')

    def __call__(self, input_path, output_path):
        return self.superres_file_openai(input_path, output_path)

    # ####################### #
    # ## functions ########## #
    # ####################### #

    def superres_file_openai(self, input_path, output_path):

        png_path = Path(input_path).with_suffix(".png")

        im = Image.open(input_path)
        im.save(str(png_path.resolve()))

        r = self.request_superres_openai(str(png_path.resolve()))

        output_url = r.json()["output_url"]

        test = urllib.FancyURLopener()
        test.addheaders = [('User-Agent', None)]
        test.retrieve(output_url, output_path)
    
    def request_superres_openai(self, img_path, tries=3):
        if tries == 0:
            raise Exception("An error has occurred")
        try:
            return requests.post(
                "https://api.deepai.org/api/torch-srgan",
                files={
                    'image': open(img_path, 'rb'),
                },
                headers={'api-key': secret.openai_id}
            )
        except:
            return self.request_colorization_openai(img_path, tries=tries-1)

