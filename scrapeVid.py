
from bs4 import BeautifulSoup
import urllib
import urlparse
from pytube import YouTube
import os
import pyimgur
import secret


imgur = pyimgur.Imgur(secret.imgur_id)


class VideoNotFoundException(Exception):
    pass


# ####################### #
# ## functions ########## #
# ####################### #

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

        vid_src = extract_video_url_from_page(submission_url)
        if vid_src is not None:
            #this is probably a mobile link to a gifv
            return download_file(vid_src)

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

