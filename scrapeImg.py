
from bs4 import BeautifulSoup
import urllib
import urlparse
from pytube import YouTube
import os
import pyimgur
import secret
import json

# todo: turn this module into a proper class


imgur = pyimgur.Imgur(secret.imgur_client_id)

user_agent = None


class VideoNotFoundException(Exception):
    pass


# ####################### #
# ## functions ########## #
# ####################### #

def extract_image_url_from_page(page_url):
    if page_url is None:
        raise VideoNotFoundException("No Video found. ")

    response = urllib.urlopen(page_url)
    info = response.info()
    if info.type == "text/html":
        soup = BeautifulSoup(response, "html.parser")

        video_src = None
        try:
            video_src = soup.source["src"]
        except (AttributeError, KeyError):
            pass
        if not video_src:
            try:
                video_src = soup.video["src"]
            except (AttributeError, KeyError):
                pass

        if not video_src:
            raise VideoNotFoundException("No Video found at " + page_url)

        if video_src.startswith("//"):
            video_src = "http:" + video_src

        return video_src
    return None

def search_and_download_image(submission, new_user_agent):
    global user_agent
    user_agent= new_user_agent

    submission_url = submission.url
    parsed_uri = urlparse.urlparse(submission_url)

    if parsed_uri.path.endswith(('.png', '.jpg', '.jpeg')):
        # this is u direct link
        return download_file(submission_url)

    if parsed_uri.netloc.endswith(".imgur.com") or parsed_uri.netloc == "imgur.com":

        if parsed_uri.path.endswith(('.png', '.jpg', '.jpeg')):
            return download_file(extract_image_url_from_page(submission_url))
        if parsed_uri.path.startswith('/a/'):
            # album
            response = urllib.urlopen(submission_url)
            soup = BeautifulSoup(response, "html.parser")
            matches = soup.select('.album-view-image-link a')
            if len(matches) > 0:
                # return first image and hope it's a video
                return download_file(matches[0]['href'])
            # return first first embedded video if there is any
            return download_file(extract_image_url_from_page(submission_url))
        if parsed_uri.path.startswith('/gallery/'):
            # gallery
            # return first first embedded video if there is any
            return download_file(extract_image_url_from_page(submission_url))

        vid_src = extract_image_url_from_page(submission_url)
        if vid_src is not None:
            # this is probably a mobile link to a gifv
            return download_file(vid_src)

        # this is link to an image, but probabldy no direct link
        img_id = os.path.basename(parsed_uri.path)
        image = imgur.get_image(img_id)
        return download_file(image.link)

    return download_file(extract_image_url_from_page(submission_url))



def download_file(video_src):
    print "download_file " + video_src
    path = urlparse.urlparse(video_src).path
    ext = os.path.splitext(path)[1]
    if not ext:
        ext = ".png"
    target_path = "input" + ext
    test = urllib.FancyURLopener()
    test.addheaders = [('User-Agent', user_agent)]
    test.retrieve(video_src, target_path)
    return target_path
