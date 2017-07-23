from gfycat.client import GfycatClient
import os
import subprocess
import praw
from praw.exceptions import APIException
from bs4 import BeautifulSoup
import urllib
import traceback
import shutil
import time
import urlparse
import pyimgur
import re
from ffprobe import FFProbe
from pytube import YouTube
import secret


# ####################### #
# ## custom exceptions ## #
# ####################### #

class VideoNotFoundException(Exception):
    pass


class VideoStabilisingException(Exception):
    pass


class VideoBrokenException(Exception):
    pass


# ####################### #
# ## functions ########## #
# ####################### #

def is_number(s):
    """ Returns True if string is a number. """
    return s.replace('.','',1).isdigit()


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
             "-vf", "vidstabtransform=smoothing=20:crop=black:zoom="+video_zoom_factor+":optzoom=0",
             output_path],
            stderr=subprocess.STDOUT)
        print "stab_file... done"
    except subprocess.CalledProcessError as cpe:
        print "cpe.returncode", cpe.returncode
        print "cpe.cmd", cpe.cmd
        print "cpe.output", cpe.output

        raise VideoStabilisingException, "ffmpeg could't compute file", cpe


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


def extract_video_url_from_page(page_url):
    if page_url is None:
        raise VideoNotFoundException("No Video found. ")

    response = urllib.urlopen(page_url)
    info = response.info()
    if info.type == "text/html":
        soup = BeautifulSoup(response, "html.parser")
        source_tag = None
        if hasattr(soup, 'source'):
            source_tag = soup.source
        elif hasattr(soup, 'video'):
            source_tag = soup.video
        else:
            raise VideoNotFoundException("No Video found at " + page_url)

        video_src = source_tag['src']
        if video_src.startswith("//"):
            video_src = "http:" + video_src
        video_type = source_tag['type']  # "video/mp4"
        if video_type is None:
            print "Warning: No Video type: "
        if not video_type.startswith("video"):
            raise VideoNotFoundException("Found File has wrong type. Found:"
                                         +video_type + ", Expected: video" )
        return video_src
    return None


def search_and_download_video(submission):
    print "getting video url..."

    submission_url = submission.url
    parsed_uri = urlparse.urlparse(submission_url)

    if parsed_uri.path.endswith(('.mp4', '.avi', 'gif', '.webm')):
        # this is u direct link
        return download_file(submission_url)

    if hasattr(submission, 'media') and submission.media is not None:
        # this is video hosted directly on reddit
        if 'duration' in submission.media:
            if submission.media.duration > max_video_length_seconds:
                raise VideoBrokenException("Video too long. Video duration: " + submission.media.duration
                                           + ", Maximum duration: " + str(max_video_length_seconds) + ". ")
        if 'fallback_url' in submission.media:
            return download_file(submission.media['fallback_url'])

    if parsed_uri.netloc.endswith(".youtube.com") \
            or parsed_uri.netloc.endswith("youtu.be"):
        yt = YouTube(submission_url)
        # get highest mp4 video and hope there is at least one.
        return download_file(yt.filter('mp4')[-1].url)
    if parsed_uri.netloc.endswith(".imgur.com") or parsed_uri.netloc == "imgur.com":

        if parsed_uri.path.endswith('.gifv'):
            return download_file(extract_video_url_from_page(submission_url))
        if parsed_uri.path.startswith('/a/'):
            # album
            response = urllib.urlopen(submission_url)
            soup = BeautifulSoup(response, "html.parser")
            matches = soup.select('.album-view-image-link a')
            if len(matches) > 0:
                # return first image and hope it's a video
                return download_file(matches[0]['href'])
            # return first first embedded video if there is any
            return download_file(extract_video_url_from_page(submission_url))
        if parsed_uri.path.startswith('/gallery/'):
            # gallery
            # return first first embedded video if there is any
            return download_file(extract_video_url_from_page(submission_url))

        # this is link to an image, but probabldy no direct link
        img_id = os.path.basename(parsed_uri.path)
        image = imgur.get_image(img_id)
        return download_file(image.link)

    return download_file(extract_video_url_from_page(submission_url))


def download_file(video_src):
    print "download_file " + video_src
    path = urlparse.urlparse(video_src).path
    ext = os.path.splitext(path)[1]
    test = urllib.FancyURLopener()
    target_path = "input" + ext
    test.retrieve(video_src, target_path)
    return target_path


def post_reply(reply_md, mention):
    print "post_reply... "
    if dryrun:
        print "reply would be:" + reply_md
        return

    try:
        mention.reply(reply_md)
    except APIException as e:
        if e.error_type == 'RATELIMIT':
            print "I was posting too fast. Error-Message: " + e.message
            wait_time_m = int(re.search(r'\d+', e.message).group()) + 1
            if wait_time_m > 10:
                wait_time_m = 10
            print "going to sleep for " + str(wait_time_m) + " minutes."
            time.sleep(wait_time_m * 60)
            mention.reply(reply_md)

        else:
            raise e

def upload_file(locale_file_name):
    print "uploading..."
    if dryrun:
        return "https://gfycat.com/FamiliarSimplisticAegeancat"
    uploaded_file_info = gfyclient.upload_from_file(locale_file_name)
    file_path =  uploaded_file_info['mp4Url'] if 'mp4Url' in uploaded_file_info else  "https://gfycat.com/" + uploaded_file_info['gfyname']
    with open(gfylinks_path, "a") as f:
        f.write(file_path + "\n")

    return file_path


def generate_reply(uploaded_url, conversion_time):
    return ""\
             "I have stabilized the video for you: " + uploaded_url + "\n\n" \
             "It took me " +  str(round(conversion_time))+ " seconds to process." \
             "\n\n ___ \n\n ^^If ^^you ^^want ^^to ^^know ^^how ^^to ^^summon ^^me: " \
             "^^[click ^^here](https://www.reddit.com/r/botwatch/comments/6p1ilf/introducing_stabbot_a_bot_that_stabilizes_videos/). "


def clear_env():
    if os.path.exists(woring_path):
        shutil.rmtree(woring_path)
    os.makedirs(woring_path)
    os.chdir(woring_path)


def mark_submission(id,posts_replied_to):
    print "marking submission " + id + " ... "
    posts_replied_to.append(id)
    with open(posts_replied_to_path, "a") as f:
        f.write(id + "\n")


def get_replied_to_list():
    if os.path.isfile(posts_replied_to_path):
        with open(posts_replied_to_path, "r") as f:
            file_content = f.read()
            file_content = file_content.split("\n")
            return list(filter(None, file_content))

    return []


def get_next_job(posts_replied_to):
    allMentions = list(reddit.inbox.mentions(limit=50))
    sorted_mentions= sorted(allMentions, key=lambda m: (m.score, m.submission.score))

    for mention in sorted_mentions:
        if not mention.new and not include_old_mentions:
            continue
        mention.mark_read()
        if not mention.is_root:
            print "comment is not root: ", mention
            continue
        if mention.submission.id in posts_replied_to:
            print "submission was alread replied to: " + mention.submission.id
            continue

        return mention


def main():
    print "starting..."
    posts_replied_to = get_replied_to_list()
    print "old replies found: " + str(len(posts_replied_to))
    while True:
        try:
            clear_env()
            mention = get_next_job(posts_replied_to)
            if mention is None:
                if debug:
                    print "No Mention found. sleeping for " + str(sleep_time_s) + " seconds ..."
                time.sleep(sleep_time_s)
                continue
            mark_submission(mention.submission.id, posts_replied_to)
            start_time = time.time()

            input_path = search_and_download_video(mention.submission)
            stab_file(input_path, "stabilized.mp4")
            uploaded_url = upload_file('stabilized.mp4')
            reply_md = generate_reply(uploaded_url, time.time() - start_time)

        except Exception as e:
            print "Exception:"
            print e.__class__, e.__doc__, e.message
            print e
            traceback.print_exc()

        else:
            try:
                if reply_md:
                    post_reply(reply_md, mention)
            except Exception as e:
                print "Exception during post_reply:"
                print e.__class__, e.__doc__, e.message
                print e
                traceback.print_exc()

        print 'sleeping for ' + str(sleep_time_s) + ' seconds ...'
        time.sleep(sleep_time_s)


# ####################### #
# ## global constants ### #
# ####################### #

reddit = praw.Reddit('my_bot',
    client_id = secret.reddit_client_id,
    client_secret = secret.reddit_client_secret,
    password = secret.reddit_password)
gfyclient = GfycatClient()
imgur = pyimgur.Imgur(secret.imgur_id)

posts_replied_to_path = os.path.abspath("data/posts_replied_to.txt")
gfylinks_path = os.path.abspath("data/gfylinks.txt")

dryrun = False
debug = False
include_old_mentions = False
woring_path = os.path.abspath("data/working")

max_video_length_seconds = 240
sleep_time_s = 10

ffmpeg_full_path = "/root/bin/ffmpeg"
video_scale_factor = "1.15"
video_zoom_factor = "-15"

# ####################### #
# ## excecution ######### #
# ####################### #

main()
