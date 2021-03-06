
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


class Colorizer(object):

    def __init__(self):
        self.client = Algorithmia.client(secret.algo_id)
        self.algo = self.client.algo('deeplearning/ColorfulImageColorization/1.1.13')

    def __call__(self, input_path, output_path):
        return self.colorize_file_openai(input_path, output_path)

    # ####################### #
    # ## functions ########## #
    # ####################### #

    def colorize_file(self, input_path, output_path):
        

        png_path = Path(input_path).with_suffix(".png")

        #if not input_path.endswith(".png"):
        im = Image.open(input_path)
        ImageOps.grayscale(im).save(str(png_path.resolve()))


        self.client.file("data://.my/colorbot/uncolorized.png").putFile(str(png_path.resolve()))


        result = self.algo.pipe({
            'image': "data://.my/colorbot/uncolorized.png"
        }).result

        result_file = self.client.file(result["output"]).getFile()
        result_file_name = result_file.name
        result_file.close()

        shutil.move(result_file_name, output_path)

    def colorize_file_openai(self, input_path, output_path):

        png_path = Path(input_path).with_suffix(".png")

        im = Image.open(input_path)
        ImageOps.grayscale(im).save(str(png_path))

        output_url = self.request_colorization_openai(str(png_path.resolve()))

        test = urllib.FancyURLopener()
        test.addheaders = [('User-Agent', None)]
        test.retrieve(output_url, output_path)
    
    def request_colorization_openai(self, img_path, tries=3):
        if tries == 0:
            raise Exception("An error has occurred")
        try:
            return requests.post(
                "https://api.deepai.org/api/colorizer",
                files={
                    'image': open(img_path, 'rb'),
                },
                headers={'api-key': secret.openai_id}
            ).json()["output_url"]
        except:
            return self.request_colorization_openai(img_path, tries=tries-1)

