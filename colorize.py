
import subprocess
from ffprobe import FFProbe

from helper import is_number

import Algorithmia

import secret

from PIL import Image

from pathlib import Path

import shutil

import os

class VideoStabilisingException(Exception):
    pass


class VideoBrokenException(Exception):
    pass


class Colorizer(object):

    def __init__(self):
        self.client = Algorithmia.client(secret.algo_id)
        self.algo = self.client.algo('deeplearning/ColorfulImageColorization/1.1.13')

    def __call__(self, input_path, output_path):
        return self.colorize_file(input_path, output_path)

    # ####################### #
    # ## functions ########## #
    # ####################### #

    def colorize_file(self, input_path, output_path):
        

        png_path = Path(input_path).with_suffix(".png")

        if not input_path.endswith(".png"):
            im = Image.open(input_path)
            im.save(png_path)


        self.client.file("data://.my/colorbot/uncolorized.png").putFile(png_path)


        result = self.algo.pipe({
            'image': "data://.my/colorbot/uncolorized.png"
        }).result

        result_file = self.client.file(result["output"]).getFile()
        result_file_name = result_file.name
        result_file.close()

        shutil.move(result_file_name, output_path)
