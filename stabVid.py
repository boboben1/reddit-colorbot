
import subprocess
from ffprobe import FFProbe

from helper import is_number


class VideoStabilisingException(Exception):
    pass


class VideoBrokenException(Exception):
    pass


class StabVid(object):

    def __init__(self,
                 ffmpeg_full_path= "/root/bin/ffmpeg",
                 video_scale_factor = "1.15",
                 video_zoom_factor= "-15",
                 max_video_length_seconds = 240):
        self.max_video_length_seconds = max_video_length_seconds
        self.ffmpeg_full_path = ffmpeg_full_path
        self.video_scale_factor = video_scale_factor
        self.video_zoom_factor = video_zoom_factor

    def __call__(self, input_path, output_path):
        return self.stab_file(input_path, output_path)

    # ####################### #
    # ## functions ########## #
    # ####################### #

    def stab_file(self, input_path, output_path):

        zoomed_file_name = "zoomed.mp4"
        metadata = FFProbe(input_path)
        if len(metadata.video) > 1:
            raise VideoBrokenException("Video may not contain multiple video streams")
        if len(metadata.video) < 1:
            raise VideoBrokenException("No video streams found in file")

        could_check_dur_initially = self.check_vid_duration(input_path)

        try:
            # zoom by the size of the zoom in the stabilization, the total output file is bigger,
            # but no resolution is lost to the crop
            subprocess.check_output(
                [self.ffmpeg_full_path,
                 "-y",
                 "-i", input_path,
                 "-vf", "scale=trunc((iw*"+self.video_scale_factor+")/2)*2:trunc(ow/a/2)*2",
                 "-pix_fmt", "yuv420p", # workaround for https://github.com/georgmartius/vid.stab/issues/36
                 zoomed_file_name],
                stderr=subprocess.STDOUT)

            if not could_check_dur_initially:
                # sometimes metadata on original vids were broken,
                # so we need to re-check after fixing it during the first ffmpeg-pass
                self.check_vid_duration(zoomed_file_name)

            subprocess.check_output(
                [self.ffmpeg_full_path,
                 "-y",
                 "-i", zoomed_file_name,
                 "-vf", "vidstabdetect",
                 "-f", "null",
                 "-"],
                stderr=subprocess.STDOUT)

            subprocess.check_output(
                [self.ffmpeg_full_path,
                 "-y",
                 "-i", zoomed_file_name,
                 "-vf", "vidstabtransform=smoothing=20:crop=black:zoom="+self.video_zoom_factor
                        + ":optzoom=0,unsharp=5:5:0.8:3:3:0.4",
                 output_path],
                stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as cpe:
            print "cpe.returncode", cpe.returncode
            print "cpe.cmd", cpe.cmd
            print "cpe.output", cpe.output

            raise VideoStabilisingException, "ffmpeg could't compute file", cpe

    def check_vid_duration(self, path):
        metadata = FFProbe(path)
        if hasattr(metadata.video[0], "duration") \
            and is_number(metadata.video[0].duration):
            if float(metadata.video[0].duration) > self.max_video_length_seconds:
                raise VideoBrokenException("Video too long. Video duration: " + metadata.video[0].duration
                                           + ", Maximum duration: " + str(self.max_video_length_seconds) + ". ")
            else:
                return True
        return False

