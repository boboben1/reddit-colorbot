
import subprocess
from ffprobe import FFProbe

# todo: turn this module into a proper class

# ####################### #
# ## global constants ### #
# ####################### #


max_video_length_seconds = 240

ffmpeg_full_path = "/root/bin/ffmpeg"
video_scale_factor = "1.15"
video_zoom_factor = "-15"


# ####################### #
# ## custom exceptions ## #
# ####################### #


class VideoStabilisingException(Exception):
    pass


class VideoBrokenException(Exception):
    pass


# ####################### #
# ## functions ########## #
# ####################### #

def stab_file(input_path, output_path):

    zoomed_file_name = "zoomed.mp4"
    print "probing file... "
    metadata = FFProbe(input_path)
    if len(metadata.video) > 1:
        raise VideoBrokenException("Video may not contain multiple video streams")
    if len(metadata.video) < 1:
        raise VideoBrokenException("Video contains no video streams")

    could_check_dur_initially = check_vid_duration(input_path)

    try:
        print "zooming..."
        # zoom by the size of the zoom in the stabilization, the total output file is bigger,
        # but no resolution is lost to the crop
        subprocess.check_output(
            [ffmpeg_full_path,
             "-y",
             "-i", input_path,
             "-vf", "scale=trunc((iw*"+video_scale_factor+")/2)*2:trunc(ow/a/2)*2",
             "-pix_fmt", "yuv420p", # workaround for https://github.com/georgmartius/vid.stab/issues/36
             zoomed_file_name],
            stderr=subprocess.STDOUT)

        if not could_check_dur_initially:
            # sometimes metadata on original vids were broken, so we need to re-check after fixing it during the first ffmpeg-pass
            check_vid_duration(zoomed_file_name)

        print "detecting ..."
        subprocess.check_output(
            [ffmpeg_full_path,
             "-y",
             "-i", zoomed_file_name,
             "-vf", "vidstabdetect",
             "-f", "null",
             "-"],
            stderr=subprocess.STDOUT)

        print "applying transformation..."
        subprocess.check_output(
            [ffmpeg_full_path,
             "-y",
             "-i", zoomed_file_name,
             "-vf", "vidstabtransform=smoothing=20:crop=black:zoom="+video_zoom_factor
                    + ":optzoom=0,unsharp=5:5:0.8:3:3:0.4",
             output_path],
            stderr=subprocess.STDOUT)
        print "stab_file... done"
    except subprocess.CalledProcessError as cpe:
        print "cpe.returncode", cpe.returncode
        print "cpe.cmd", cpe.cmd
        print "cpe.output", cpe.output

        raise VideoStabilisingException, "ffmpeg could't compute file", cpe



def is_number(s):
    """ Returns True if string is a number. """
    return s.replace('.','',1).isdigit()


def check_vid_duration(path):
    metadata = FFProbe(path)
    if hasattr(metadata.video[0], "duration") \
        and is_number(metadata.video[0].duration):
        if float(metadata.video[0].duration) > max_video_length_seconds:
            raise VideoBrokenException("Video too long. Video duration: " + metadata.video[0].duration
                                       + ", Maximum duration: " + str(max_video_length_seconds) + ". ")
        else:
            return True
    return False

